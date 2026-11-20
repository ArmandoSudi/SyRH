"""Editing the flat reference lists through the API. See specs/2026-11-20-reference-data-screens."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import EntreeAudit

from .models import Fonction

FONCTIONS = "/api/referentiels/fonctions/"
D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)


def member(username, *groups):
    user = get_user_model().objects.create_user(username, password="x")
    user.groups.set(Group.objects.filter(name__in=groups))
    return user


class EditionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière")
        cls.remuneration = member("remuneration", "Rémunération")
        cls.admin = member("admin", "Administrateur système")
        cls.auditeur = member("auditeur", "Auditeur")
        cls.nobody = member("personne")

    def client_for(self, user):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client


class FonctionEditionTests(EditionTestCase):
    """The generic write operations, on fonctions (D3 to D9)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.jur = Fonction.objects.create(
            code="JUR", nom="Juriste", nature="execution", date_ouverture=D2015
        )

    def setUp(self):
        self.api = self.client_for(self.carriere)

    def create(self, **values):
        data = {"code": "cpt", "nom": "Comptable", "nature": "execution",
                "date_ouverture": "2015-01-01", **values}  # fmt: skip
        return self.api.post(FONCTIONS, data, format="json")

    # Create

    def test_editor_creates_a_row_and_is_its_author(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual((body["code"], body["nature_libelle"]), ("CPT", "Exécution"))
        row = Fonction.objects.get(pk=body["id"])
        self.assertEqual((row.cree_par, row.modifie_par), (self.carriere, self.carriere))
        entry = EntreeAudit.objects.get(table__model="fonction", objet_id=row.pk)
        self.assertEqual((entry.auteur, entry.objet_libelle), (self.carriere, "CPT — Comptable"))

    def test_model_rules_come_back_on_their_fields(self):
        response = self.create(code="jur", date_ouverture="2020-01-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("porte déjà ce code", response.json()["non_field_errors"][0])

        response = self.create(date_ouverture="2020-01-01", date_fermeture="2015-01-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("postérieure à la date d'ouverture", response.json()["date_fermeture"][0])

        response = self.create(nom="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("nom", response.json())
        self.assertEqual(Fonction.objects.count(), 1)

    def test_client_cannot_set_the_authors_or_dates_of_creation(self):
        response = self.create(cree_par=self.admin.pk, date_creation="2000-01-01T00:00:00Z")
        self.assertEqual(response.status_code, 201)
        row = Fonction.objects.get(code="CPT")
        self.assertEqual(row.cree_par, self.carriere)
        self.assertNotEqual(row.date_creation.year, 2000)

    # Correct

    def test_editor_corrects_a_row_in_place(self):
        response = self.api.patch(f"{FONCTIONS}{self.jur.pk}/", {"nom": "Juriste principal"},
                                  format="json")  # fmt: skip
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nom"], "Juriste principal")
        self.jur.refresh_from_db()
        self.assertEqual((self.jur.nom, self.jur.modifie_par), ("Juriste principal", self.carriere))

    def test_setting_a_closing_date_closes_the_row(self):
        response = self.api.patch(f"{FONCTIONS}{self.jur.pk}/", {"date_fermeture": "2020-01-01"},
                                  format="json")  # fmt: skip
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Fonction.objects.ouvertes(D2020).exists())

    def test_correction_errors_come_back_and_nothing_changes(self):
        response = self.api.patch(f"{FONCTIONS}{self.jur.pk}/", {"date_fermeture": "2014-01-01"},
                                  format="json")  # fmt: skip
        self.assertEqual(response.status_code, 400)
        self.assertIn("date_fermeture", response.json())
        self.jur.refresh_from_db()
        self.assertIsNone(self.jur.date_fermeture)

    # Close and succeed

    def successeur(self, pk, **values):
        return self.api.post(f"{FONCTIONS}{pk}/successeur/", values, format="json")

    def test_successor_closes_the_row_and_opens_the_new_one(self):
        response = self.successeur(self.jur.pk, date_effet="2020-01-01", nom="Juriste conseil")
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(
            (body["code"], body["nom"], body["nature"], body["date_ouverture"],
             body["date_fermeture"]),
            ("JUR", "Juriste conseil", "execution", "2020-01-01", None),
        )  # fmt: skip
        self.jur.refresh_from_db()
        self.assertEqual(self.jur.date_fermeture, D2020)

        def name_on(day):
            return Fonction.objects.ouvertes(day).get(code="JUR").nom

        self.assertEqual(name_on(date(2019, 12, 31)), "Juriste")
        self.assertEqual(name_on(D2020), "Juriste conseil")
        successor = Fonction.objects.get(pk=body["id"])
        self.assertEqual(successor.cree_par, self.carriere)

    def test_successor_needs_a_date_after_the_opening(self):
        for value in ("2015-01-01", "2014-06-01"):
            with self.subTest(value):
                response = self.successeur(self.jur.pk, date_effet=value)
                self.assertEqual(response.status_code, 400)
                self.assertIn("postérieure à l'ouverture", response.json()["date_effet"][0])
        response = self.successeur(self.jur.pk)
        self.assertIn("date_effet", response.json())
        self.jur.refresh_from_db()
        self.assertIsNone(self.jur.date_fermeture)

    def test_a_closed_row_cannot_be_succeeded(self):
        closed = Fonction.objects.create(code="OLD", nom="Ancienne", nature="execution",
                                         date_ouverture=D2015, date_fermeture=D2020)  # fmt: skip
        response = self.successeur(closed.pk, date_effet="2018-01-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("déjà fermée", response.json()["date_effet"][0])

    def test_an_invalid_successor_leaves_the_row_open(self):
        response = self.successeur(self.jur.pk, date_effet="2020-01-01", nature="inconnue")
        self.assertEqual(response.status_code, 400)
        self.assertIn("nature", response.json())
        self.jur.refresh_from_db()
        self.assertIsNone(self.jur.date_fermeture)
        self.assertEqual(Fonction.objects.count(), 1)

    def test_successor_ignores_dates_sent_by_the_client(self):
        response = self.successeur(
            self.jur.pk, date_effet="2020-01-01", date_ouverture="2016-01-01",
            date_fermeture="2030-01-01",
        )  # fmt: skip
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            (response.json()["date_ouverture"], response.json()["date_fermeture"]),
            ("2020-01-01", None),
        )

    # Permissions

    def test_anonymous_and_readers_cannot_write(self):
        detail = f"{FONCTIONS}{self.jur.pk}/"
        anonymous = self.client_for(None)
        self.assertEqual(anonymous.post(FONCTIONS, {}, format="json").status_code, 401)
        for user in (self.auditeur, self.remuneration, self.nobody):
            client = self.client_for(user)
            with self.subTest(user.username):
                self.assertEqual(client.post(FONCTIONS, {}, format="json").status_code, 403)
                self.assertEqual(client.patch(detail, {}, format="json").status_code, 403)
                self.assertEqual(
                    client.post(f"{detail}successeur/", {}, format="json").status_code, 403
                )
        self.assertEqual(self.client_for(self.auditeur).get(FONCTIONS).status_code, 200)

    def test_put_and_delete_are_not_allowed(self):
        detail = f"{FONCTIONS}{self.jur.pk}/"
        for user in (self.carriere, self.admin, self.auditeur):
            client = self.client_for(user)
            with self.subTest(user.username):
                self.assertEqual(client.put(detail, {}, format="json").status_code, 405)
                self.assertEqual(client.delete(detail).status_code, 405)
        self.assertTrue(Fonction.objects.filter(pk=self.jur.pk).exists())

    def test_administrator_writes_too(self):
        response = self.client_for(self.admin).post(FONCTIONS, {
            "code": "X", "nom": "X", "nature": "execution", "date_ouverture": "2015-01-01"},
            format="json")  # fmt: skip
        self.assertEqual(response.status_code, 201)

    def test_session_write_without_csrf_token_is_refused(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.carriere)
        response = client.post(FONCTIONS, {"code": "X"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.json()["detail"])
