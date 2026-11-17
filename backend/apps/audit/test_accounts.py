from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.roles import ADMIN_GROUP, sync_groups

from .models import COMPTES, EntreeAudit
from .values import MASK

Action = EntreeAudit.Action
PASSWORD = "Kinshasa-2026-rh"


def entries_for(obj):
    return EntreeAudit.objects.filter(
        table=ContentType.objects.get_for_model(obj), objet_id=obj.pk
    ).order_by("id")


class AccountAdminCaptureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("admin.syrh", password=PASSWORD, is_staff=True)
        cls.admin.groups.add(Group.objects.get(name=ADMIN_GROUP))
        cls.agent = User.objects.create_user("mkabila", password=PASSWORD, first_name="Marie")

    def setUp(self):
        self.client.force_login(self.admin)

    def user_form(self, **overrides):
        joined = timezone.localtime(self.agent.date_joined)
        data = {
            "username": self.agent.username,
            "first_name": self.agent.first_name,
            "last_name": "",
            "email": "",
            "is_active": "on",
            "groups": [g.pk for g in self.agent.groups.all()],
            "user_permissions": [],
            "date_joined_0": joined.strftime("%d/%m/%Y"),
            "date_joined_1": joined.strftime("%H:%M:%S"),
        }
        return data | overrides

    def post_user(self, **overrides):
        url = reverse("admin:accounts_user_change", args=[self.agent.pk])
        response = self.client.post(url, self.user_form(**overrides))
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", None))

    def test_group_membership_change_is_logged(self):
        social = Group.objects.get(name="Social")

        self.post_user(groups=[social.pk])

        entry = entries_for(self.agent).last()
        self.assertEqual(entry.action, Action.MODIFICATION)
        self.assertEqual(entry.auteur, self.admin)
        self.assertEqual(entry.module, COMPTES)
        self.assertEqual(
            entry.changements,
            [{"champ": "groups", "libelle": "groupes", "ajoutes": ["Social"], "retires": []}],
        )

    def test_field_change_is_logged(self):
        self.post_user(first_name="Mariam")

        entry = entries_for(self.agent).last()
        self.assertEqual(
            entry.changements,
            [{"champ": "first_name", "libelle": "prénom", "avant": "Marie", "apres": "Mariam"}],
        )

    def test_unchanged_form_writes_nothing(self):
        before = entries_for(self.agent).count()

        self.post_user()

        self.assertEqual(entries_for(self.agent).count(), before)

    def test_group_permissions_change_is_logged(self):
        group = Group.objects.get(name="Formation")
        removed = Permission.objects.get(codename="access_agents")
        added = Permission.objects.get(codename="access_carriere")
        kept = group.permissions.exclude(pk=removed.pk)
        url = reverse("admin:auth_group_change", args=[group.pk])

        response = self.client.post(
            url, {"name": group.name, "permissions": [p.pk for p in kept] + [added.pk]}
        )

        self.assertEqual(response.status_code, 302)
        entry = entries_for(group).last()
        self.assertEqual(entry.auteur, self.admin)
        self.assertEqual(
            entry.changements,
            [
                {
                    "champ": "permissions",
                    "libelle": "permissions",
                    "ajoutes": ["Accès au module Carrière"],
                    "retires": ["Accès au module Agents"],
                }
            ],
        )

    def test_admin_password_change_is_masked(self):
        url = reverse("admin:auth_user_password_change", args=[self.agent.pk])

        response = self.client.post(
            url,
            {
                "password1": "Gombe-fleuve-0417",
                "password2": "Gombe-fleuve-0417",
                "usable_password": "true",
            },
        )

        self.assertEqual(response.status_code, 302)
        entry = entries_for(self.agent).last()
        self.assertEqual(entry.auteur, self.admin)
        self.assertEqual(
            entry.changements,
            [{"champ": "password", "libelle": "mot de passe", "avant": MASK, "apres": MASK}],
        )
        self.agent.refresh_from_db()
        self.assertNotIn(self.agent.password, str(entry.changements))


class OwnAccountCaptureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("mkabila", password=PASSWORD)

    def test_own_password_change_is_masked(self):
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.post(
            reverse("auth-password"),
            {"old_password": PASSWORD, "new_password": "Gombe-fleuve-0417"},
            format="json",
        )

        self.assertEqual(response.status_code, 204)
        entry = entries_for(self.user).last()
        self.assertEqual(entry.auteur, self.user)
        self.assertEqual(entry.changements[0]["apres"], MASK)
        self.assertFalse(EntreeAudit.objects.filter(changements__icontains="pbkdf2").exists())

    def test_signing_in_writes_nothing(self):
        before = EntreeAudit.objects.count()

        response = APIClient().post(
            reverse("auth-login"), {"username": "mkabila", "password": PASSWORD}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(EntreeAudit.objects.count(), before)


class GroupSetupCaptureTests(TestCase):
    def test_migrate_logged_each_group_creation_without_author(self):
        created = EntreeAudit.objects.filter(
            table=ContentType.objects.get_for_model(Group), action=Action.CREATION
        )

        self.assertEqual(created.count(), Group.objects.count())
        self.assertFalse(created.exclude(auteur=None).exists())
        self.assertTrue(created.filter(changements__contains=[{"champ": "permissions"}]).exists())

    def test_sync_logs_what_it_adds_then_nothing(self):
        group = Group.objects.get(name="Auditeur")
        group.permissions.remove(Permission.objects.get(codename="access_audit"))
        before = EntreeAudit.objects.count()

        sync_groups()
        sync_groups()

        self.assertEqual(EntreeAudit.objects.count(), before + 1)
        entry = entries_for(group).last()
        self.assertIsNone(entry.auteur)
        self.assertEqual(entry.changements[0]["ajoutes"], ["Accès au module Journal d'audit"])

    def test_access_audit_is_for_three_profiles(self):
        holders = set(
            Group.objects.filter(permissions__codename="access_audit").values_list(
                "name", flat=True
            )
        )

        self.assertEqual(holders, {"Auditeur", "Direction RH", ADMIN_GROUP})
