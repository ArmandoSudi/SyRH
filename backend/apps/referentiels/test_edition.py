"""Editing the flat reference lists through the API. See specs/2026-11-20-reference-data-screens."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import EntreeAudit

from .models import (
    Banque,
    Fonction,
    MotifSortie,
    Parametre,
    TypeContrat,
    TypeDocument,
    TypeSuspension,
)

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


class OtherListsEditionTests(EditionTestCase):
    """The same three writes on the five other flat lists, with one rule each coming
    back on its field, and the editors of each (D3 to D8)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.ldm = TypeDocument.objects.create(code="LDM", nom="Lettre", date_ouverture=D2015)
        cls.dec = TypeDocument.objects.create(code="DEC", nom="Décision", date_ouverture=D2015)
        cls.cdi = TypeContrat.objects.create(code="CDI", nom="CDI", duree_determinee=False,
                                             periode_essai=True, date_ouverture=D2015)  # fmt: skip
        cls.bcf = Banque.objects.create(code="BCF", nom="Fleuve", swift="BCFLCDKI",
                                        date_ouverture=D2015)  # fmt: skip
        cls.dem = MotifSortie.objects.create(code="DEM", nom="Démission", type_document=cls.ldm,
                                             date_ouverture=D2015)  # fmt: skip
        cls.deta = TypeSuspension.objects.create(code="DETA", nom="Détachement",
                                                 type_document=cls.dec, compte_anciennete=True,
                                                 date_ouverture=D2015)  # fmt: skip
        cls.retraite = Parametre.objects.create(cle="age_retraite", valeur=65,
                                                date_ouverture=D2015)  # fmt: skip

    def post(self, user, url, data):
        return self.client_for(user).post(url, data, format="json")

    def patch(self, user, url, data):
        return self.client_for(user).patch(url, data, format="json")

    def test_contract_types(self):
        url = "/api/referentiels/types-contrat/"
        created = self.post(self.carriere, url, {"code": "stg", "nom": "Stage",
                            "duree_determinee": True, "periode_essai": False,
                            "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["code"], "STG")
        corrected = self.patch(self.carriere, f"{url}{self.cdi.pk}/", {"periode_essai": False})
        self.assertFalse(corrected.json()["periode_essai"])
        succ = self.post(self.carriere, f"{url}{self.cdi.pk}/successeur/",
                         {"date_effet": "2020-01-01", "periode_essai": True})  # fmt: skip
        self.assertEqual((succ.status_code, succ.json()["code"]), (201, "CDI"))

    def test_banks_and_their_swift_rule(self):
        url = "/api/referentiels/banques/"
        refused = self.post(self.remuneration, url, {"code": "X", "nom": "X", "swift": "ABC",
                                                     "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(refused.status_code, 400)
        self.assertIn("Code SWIFT/BIC invalide", refused.json()["swift"][0])
        created = self.post(self.remuneration, url, {"code": "trc", "nom": "Trésor",
                            "swift": "trcrcdki", "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual((created.status_code, created.json()["swift"]), (201, "TRCRCDKI"))
        merged = self.post(self.remuneration, f"{url}{self.bcf.pk}/successeur/",
                           {"date_effet": "2022-01-01", "nom": "Fleuve Union"})  # fmt: skip
        self.assertEqual((merged.status_code, merged.json()["swift"]), (201, "BCFLCDKI"))
        self.assertEqual(Banque.objects.get(pk=created.json()["id"]).cree_par, self.remuneration)

    def test_exit_reasons_and_the_retirement_and_death_rule(self):
        url = "/api/referentiels/motifs-sortie/"
        refused = self.post(self.carriere, url, {"code": "X", "nom": "X",
                            "type_document": self.ldm.pk, "retraite": True, "deces": True,
                            "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(refused.status_code, 400)
        self.assertIn("à la fois une retraite et un décès", refused.json()["deces"][0])
        moved = self.patch(self.carriere, f"{url}{self.dem.pk}/", {"type_document": self.dec.pk})
        self.assertEqual(moved.json()["type_document_libelle"], "DEC — Décision")
        succ = self.post(self.carriere, f"{url}{self.dem.pk}/successeur/",
                         {"date_effet": "2020-01-01", "type_document": self.ldm.pk})  # fmt: skip
        self.assertEqual((succ.status_code, succ.json()["type_document"]), (201, self.ldm.pk))

    def test_suspension_types_and_the_zero_months_rule(self):
        url = "/api/referentiels/types-suspension/"
        refused = self.post(self.carriere, url, {"code": "X", "nom": "X",
                            "type_document": self.dec.pk, "compte_anciennete": False,
                            "duree_max_mois": 0, "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(refused.status_code, 400)
        self.assertIn("au moins un mois", refused.json()["duree_max_mois"][0])
        created = self.post(self.carriere, url, {"code": "dispo", "nom": "Disponibilité",
                            "type_document": self.dec.pk, "compte_anciennete": False,
                            "duree_max_mois": 24, "renouvellements_max": 1,
                            "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.patch(self.carriere, f"{url}{self.deta.pk}/",
                                    {"duree_max_mois": None}).status_code, 200)  # fmt: skip

    def test_parameters_bounds_and_fixed_key(self):
        url = "/api/referentiels/parametres/"
        refused = self.patch(self.carriere, f"{url}{self.retraite.pk}/", {"valeur": 650})
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()["valeur"], ["Entre 55 et 75 ans."])
        key = self.patch(self.carriere, f"{url}{self.retraite.pk}/", {"cle": "duree_carriere"})
        self.assertEqual(key.status_code, 400)
        self.assertIn("Ne peut pas être modifié", key.json()["cle"][0])
        succ = self.post(self.carriere, f"{url}{self.retraite.pk}/successeur/",
                         {"date_effet": "2025-01-01", "valeur": 63})  # fmt: skip
        self.assertEqual(succ.status_code, 201)
        self.assertEqual(Parametre.valeur_au("age_retraite", date(2024, 12, 31)), 65)
        self.assertEqual(Parametre.valeur_au("age_retraite", date(2025, 1, 1)), 63)
        self.assertEqual(succ.json()["cle_libelle"], "Âge de la retraite")

    def test_each_table_is_written_by_its_own_editors(self):
        tables = {
            "/api/referentiels/types-contrat/": self.cdi,
            "/api/referentiels/motifs-sortie/": self.dem,
            "/api/referentiels/types-suspension/": self.deta,
            "/api/referentiels/parametres/": self.retraite,
            "/api/referentiels/banques/": self.bcf,
        }
        banks = "/api/referentiels/banques/"
        for url, obj in tables.items():
            detail = f"{url}{obj.pk}/"
            allowed = {self.admin} | ({self.remuneration} if url == banks else {self.carriere})
            for user in (self.carriere, self.remuneration, self.admin, self.auditeur):
                with self.subTest(url=url, user=user.username):
                    status = self.patch(user, detail, {}).status_code
                    self.assertEqual(status, 200 if user in allowed else 403)
                    self.assertEqual(self.client_for(user).delete(detail).status_code, 405)
