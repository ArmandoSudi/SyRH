"""Searching the agents. See specs/2026-11-22-agent-list (D4 to D11)."""

from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.referentiels.models import Categorie, Grade, TypeContrat

from .models import Affectation, Agent, Classement, CompteBancaire, Contrat
from .test_access import member
from .test_affectations import D2015, agent
from .test_affectations import Base as PositionBase
from .test_classements import echelon

AGENTS = "/api/agents/"


class Base(PositionBase):
    """The position tests' agents (Mukendi and Nsimba: CDD 2020, CDI 2022), plus:
    Kabongo Élodie, CDI from 2027 (à venir); Ilunga, no contract. Mukendi works in the
    service under DGC (département) under DRH from 2020, moves to the bureau in 2023;
    Nsimba works at DRH directly as Juriste."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cat = Categorie.objects.create(code="A", nom="Cadres", rang=3, date_ouverture=D2015)
        cls.a1 = Grade.objects.create(code="A1", nom="Attaché 1", categorie=cat, rang=1,
                                      date_ouverture=D2015)  # fmt: skip
        cls.a2 = Grade.objects.create(code="A2", nom="Attaché 2", categorie=cat, rang=2,
                                      date_ouverture=D2015)  # fmt: skip
        a1e1, a2e1 = echelon(cls.a1, 1), echelon(cls.a2, 1)
        cdi = TypeContrat.objects.get(code="CDI")
        cls.mukendi = cls.agent
        cls.mukendi.prenom = "Jean"
        cls.mukendi.save()
        cls.nsimba = cls.other
        cls.elodie = agent("ARPTC/0003/2027", "Kabongo")
        cls.elodie.prenom = "Élodie"
        cls.elodie.save()
        Contrat.objects.create(agent=cls.elodie, type_contrat=cdi, date_debut=date(2027, 1, 1))
        cls.ilunga = agent("ARPTC/0004/2020", "Ilunga")
        for jour, unite in ((date(2020, 3, 1), cls.svc), (date(2023, 1, 1), cls.bur)):
            Affectation.objects.create(agent=cls.mukendi, unite=unite, fonction=cls.chef,
                                       date_effet=jour)  # fmt: skip
        Affectation.objects.create(agent=cls.nsimba, unite=cls.drh, fonction=cls.juriste,
                                   date_effet=date(2020, 3, 1))  # fmt: skip
        Classement.objects.create(agent=cls.mukendi, echelon=a1e1, date_effet=date(2020, 3, 1))
        Classement.objects.create(agent=cls.mukendi, echelon=a2e1, date_effet=date(2022, 6, 1))
        Classement.objects.create(agent=cls.nsimba, echelon=a1e1, date_effet=date(2020, 3, 1))
        cls.reader = member("formation", "Formation")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.reader)

    def ids(self, **params):
        response = self.client.get(AGENTS, {"date": "2024-06-01", **params})
        self.assertEqual(response.status_code, 200, response.json())
        return [row["id"] for row in response.json()["results"]]


class TextTests(Base):
    def test_matricule_and_names_ignoring_case_and_accents(self):
        self.assertEqual(self.ids(q="0002"), [self.nsimba.pk])
        self.assertEqual(self.ids(q="MUKENDI"), [self.mukendi.pk])
        self.assertEqual(self.ids(q="elodie"), [self.elodie.pk])
        self.assertEqual(self.ids(q="ÉLODIE"), [self.elodie.pk])

    def test_every_word_must_match(self):
        self.assertEqual(self.ids(q="muk jean"), [self.mukendi.pk])
        self.assertEqual(self.ids(q="muk elodie"), [])


class PositionFilterTests(Base):
    def test_unit_includes_sub_units(self):
        self.assertEqual(set(self.ids(unite=self.drh.pk)), {self.mukendi.pk, self.nsimba.pk})
        self.assertEqual(self.ids(unite=self.dep.pk), [self.mukendi.pk])

    def test_unit_at_a_date(self):
        # Moved from the service to its bureau in 2023: the service still holds him.
        self.assertEqual(self.ids(unite=self.bur.pk), [self.mukendi.pk])
        self.assertEqual(self.ids(unite=self.bur.pk, date="2021-01-01"), [])
        self.assertEqual(self.ids(unite=self.svc.pk, date="2021-01-01"), [self.mukendi.pk])

    def test_function_and_grade_at_a_date(self):
        self.assertEqual(self.ids(fonction=self.juriste.pk), [self.nsimba.pk])
        self.assertEqual(self.ids(grade=self.a2.pk), [self.mukendi.pk])
        self.assertEqual(
            set(self.ids(grade=self.a1.pk, date="2021-01-01")), {self.mukendi.pk, self.nsimba.pk}
        )


class StatusFilterTests(Base):
    def test_one_or_several_statuses_and_default_all(self):
        self.assertEqual(set(self.ids(statut="actif")), {self.mukendi.pk, self.nsimba.pk})
        self.assertEqual(self.ids(statut="a_venir"), [self.elodie.pk])
        self.assertEqual(
            set(self.ids(statut="a_venir,sans_contrat")), {self.elodie.pk, self.ilunga.pk}
        )
        self.assertEqual(len(self.ids()), 4)
        self.assertEqual(set(self.ids(statut="inactif", date="2021-06-01")),
                         {self.mukendi.pk, self.nsimba.pk})  # fmt: skip

    def test_rows_carry_status_and_positions_on_the_date(self):
        rows = self.client.get(AGENTS, {"date": "2021-01-01", "q": "mukendi"}).json()["results"]
        row = rows[0]
        self.assertEqual((row["statut"], row["statut_libelle"]), ("actif", "En activité"))
        self.assertEqual(row["affectation_actuelle"]["unite_code"], "SCAR")
        self.assertEqual(row["classement_actuel"]["grade_code"], "A1")


class CombineSortPageTests(Base):
    def test_filters_combine(self):
        self.assertEqual(self.ids(unite=self.drh.pk, grade=self.a1.pk), [self.nsimba.pk])
        self.assertEqual(self.ids(q="mukendi", statut="a_venir"), [])

    def test_sorts(self):
        by_name = self.ids()
        self.assertEqual(by_name, [self.ilunga.pk, self.elodie.pk, self.mukendi.pk, self.nsimba.pk])
        by_matricule = self.ids(tri="matricule")
        expected = sorted(Agent.objects.all(), key=lambda a: a.matricule)
        self.assertEqual(by_matricule, [a.pk for a in expected])

    def test_pagination(self):
        response = self.client.get(AGENTS, {"taille": 3}).json()
        self.assertEqual(set(response), {"count", "next", "previous", "results"})
        self.assertEqual((response["count"], len(response["results"])), (4, 3))
        self.assertIn("page=2", response["next"])
        self.assertEqual(
            len(self.client.get(AGENTS, {"taille": 3, "page": 2}).json()["results"]), 1
        )
        self.assertEqual(self.client.get(AGENTS, {"page": 9}).status_code, 404)

    def test_default_page_size_is_25(self):
        for n in range(30):
            agent(f"Z/{n:02d}", f"Zz{n:02d}")
        response = self.client.get(AGENTS).json()
        self.assertEqual((response["count"], len(response["results"])), (34, 25))

    def test_fixed_number_of_queries_per_page(self):
        self.client.get(AGENTS, {"unite": self.drh.pk})
        with CaptureQueriesContext(connection) as few:
            self.client.get(AGENTS, {"unite": self.drh.pk, "q": "a"})
        cdi = TypeContrat.objects.get(code="CDI")
        for n in range(10):
            other = agent(f"Y/{n}", f"Agent {n}")
            Contrat.objects.create(agent=other, type_contrat=cdi, date_debut=date(2020, 3, 1))
            Affectation.objects.create(agent=other, unite=self.svc, fonction=self.chef,
                                       date_effet=date(2020, 3, 1))  # fmt: skip
        with CaptureQueriesContext(connection) as many:
            self.client.get(AGENTS, {"unite": self.drh.pk, "q": "a"})
        self.assertEqual(len(few), len(many))


class ErrorTests(Base):
    def test_bad_parameters_on_their_name(self):
        cases = [
            ({"unite": 999999}, "unite"),
            ({"grade": 999999}, "grade"),
            ({"fonction": 999999}, "fonction"),
            ({"date": "01/06/2024"}, "date"),
            ({"statut": "retraite"}, "statut"),
            ({"taille": 101}, "taille"),
            ({"tri": "age"}, "tri"),
        ]
        for params, field in cases:
            with self.subTest(params):
                response = self.client.get(AGENTS, params)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        message = self.client.get(AGENTS, {"statut": "retraite"}).json()["statut"][0]
        self.assertTrue(message.startswith("Statut inconnu : retraite."))


class LeakAndAccessTests(Base):
    def test_no_pay_or_contact_field_for_any_reader(self):
        from apps.accounts.roles import GROUPS
        from apps.referentiels.models import Banque

        bcf = Banque.objects.create(code="BCF", nom="Banque du Fleuve", date_ouverture=D2015)
        CompteBancaire.objects.create(agent=self.mukendi, banque=bcf, numero="05100 0001234",
                                      date_effet=D2015)  # fmt: skip
        for name, (_, modules) in GROUPS.items():
            if "agents" not in modules:
                continue
            with self.subTest(name):
                client = APIClient()
                client.force_authenticate(member(f"u-{len(name)}-{name[:5]}", name))
                body = client.get(AGENTS).content.decode()
                self.assertNotIn("05100", body)
                for word in ("compte", "banque", "salaire", "montant", "coordonnees", "contrats"):
                    self.assertNotIn(f'"{word}', body)

    def test_access_unchanged(self):
        self.assertEqual(APIClient().get(AGENTS).status_code, 401)
        nobody = APIClient()
        nobody.force_authenticate(member("personne"))
        self.assertEqual(nobody.get(AGENTS).status_code, 403)
