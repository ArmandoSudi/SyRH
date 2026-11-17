from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .views import LOGIN_ERROR

PASSWORD = "Kinshasa-2026-rh"
NEW_PASSWORD = "Gombe-fleuve-0417"


class UserModelTests(TestCase):
    def test_custom_user_model_is_active(self):
        user = get_user_model().objects.create_user("agent", password="x")

        self.assertEqual(user._meta.label, "accounts.User")


class AuthTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            "mkabila",
            password=PASSWORD,
            first_name="Marie",
            last_name="Kabila",
            email="mkabila@example.org",
        )

    def new_client(self):
        """A browser-like client: CSRF is enforced and the cookie is fetched first."""
        client = APIClient(enforce_csrf_checks=True)
        client.get(reverse("auth-csrf"))
        return client

    def post(self, client, name, data=None):
        token = client.cookies["csrftoken"].value if "csrftoken" in client.cookies else ""
        return client.post(reverse(name), data or {}, format="json", HTTP_X_CSRFTOKEN=token)

    def login(self, client, username="mkabila", password=PASSWORD):
        return self.post(client, "auth-login", {"username": username, "password": password})

    def setUp(self):
        self.client = self.new_client()


class PlumbingTests(AuthTestCase):
    def test_anonymous_request_gets_401_not_403(self):
        client = APIClient()
        for name in ("auth-me",):
            self.assertEqual(client.get(reverse(name)).status_code, 401)
        for name in ("auth-logout", "auth-password"):
            self.assertEqual(client.post(reverse(name)).status_code, 401)

    def test_health_stays_public(self):
        self.assertEqual(APIClient().get(reverse("health")).status_code, 200)

    def test_csrf_endpoint_is_public_and_sets_the_cookie(self):
        client = APIClient()

        response = client.get(reverse("auth-csrf"))

        self.assertEqual(response.status_code, 204)
        self.assertIn("csrftoken", response.cookies)


class LoginTests(AuthTestCase):
    def test_valid_credentials_open_a_session(self):
        response = self.login(self.client)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "mkabila")
        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["username"], "mkabila")

    def test_user_payload_has_exactly_the_public_fields(self):
        response = self.login(self.client)

        self.assertEqual(
            response.json(),
            {
                "id": self.user.pk,
                "username": "mkabila",
                "first_name": "Marie",
                "last_name": "Kabila",
                "email": "mkabila@example.org",
                "groups": [],
                "permissions": [],
            },
        )

    def test_every_failure_returns_the_same_error(self):
        get_user_model().objects.create_user("ancien", password=PASSWORD, is_active=False)
        attempts = {
            "wrong password": ("mkabila", "pas-le-bon"),
            "unknown username": ("inconnu", PASSWORD),
            "inactive account": ("ancien", PASSWORD),
            "empty fields": ("", ""),
        }

        for label, (username, password) in attempts.items():
            with self.subTest(label):
                response = self.login(self.new_client(), username, password)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"non_field_errors": [LOGIN_ERROR]})

    def test_failed_login_opens_no_session(self):
        self.login(self.client, password="pas-le-bon")

        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 401)

    def test_login_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(
            reverse("auth-login"), {"username": "mkabila", "password": PASSWORD}, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(client.get(reverse("auth-me")).status_code, 401)

    def test_session_key_changes_on_login(self):
        session = self.client.session
        session["marker"] = "x"
        session.save()
        self.client.cookies["sessionid"] = session.session_key
        before = session.session_key

        self.login(self.client)

        self.assertNotEqual(self.client.cookies["sessionid"].value, before)


class LogoutTests(AuthTestCase):
    def test_logout_ends_the_session(self):
        self.login(self.client)

        response = self.post(self.client, "auth-logout")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 401)

    def test_logout_requires_the_csrf_token(self):
        self.login(self.client)

        response = self.client.post(reverse("auth-logout"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 200)


class PasswordChangeTests(AuthTestCase):
    def change(self, client, old=PASSWORD, new=NEW_PASSWORD):
        return self.post(client, "auth-password", {"old_password": old, "new_password": new})

    def test_change_replaces_the_password(self):
        self.login(self.client)

        response = self.change(self.client)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.login(self.new_client(), password=PASSWORD).status_code, 400)
        self.assertEqual(self.login(self.new_client(), password=NEW_PASSWORD).status_code, 200)

    def test_current_session_survives_and_other_sessions_end(self):
        other = self.new_client()
        self.login(other)
        self.login(self.client)

        self.change(self.client)

        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 200)
        self.assertEqual(other.get(reverse("auth-me")).status_code, 401)

    def test_wrong_old_password_is_a_field_error(self):
        self.login(self.client)

        response = self.change(self.client, old="pas-le-bon")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(response.json()), ["old_password"])
        self.assertEqual(self.login(self.new_client()).status_code, 200)

    def test_weak_new_password_is_a_field_error(self):
        self.login(self.client)

        response = self.change(self.client, new="12345678")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(response.json()), ["new_password"])
        self.assertEqual(self.login(self.new_client()).status_code, 200)

    def test_errors_are_in_french_whatever_the_browser_language(self):
        self.login(self.client)

        response = self.client.post(
            reverse("auth-password"),
            {"old_password": PASSWORD, "new_password": "12345678"},
            format="json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
            HTTP_ACCEPT_LANGUAGE="en",
        )

        self.assertIn("Ce mot de passe est trop courant.", response.json()["new_password"])
