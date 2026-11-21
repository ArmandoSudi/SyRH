"""GET /api/agents/ (agent identity D13, D18, D19; contact details D18; contract D19)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.roles import GROUPS
from apps.referentiels.models import TypeContrat

from .models import Agent, Contrat, Coordonnees

AGENTS = "/api/agents/"
READERS = {name for name, (_, modules) in GROUPS.items() if "agents" in modules}


def member(username, *groups):
    user = get_user_model().objects.create_user(username, password="x")
    user.groups.set(Group.objects.filter(name__in=groups))
    return user


def agent(matricule, nom, **values):
    values = {
        "sexe": "M",
        "date_naissance": date(1985, 3, 14),
        "lieu_naissance": "Kinshasa",
        **values,
    }
    return Agent.objects.create(matricule=matricule, nom=nom, **values)


class AgentApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tshala = agent("C/3", "Tshala", sexe="F", prenom="Marie")
        cls.kabila = agent("B/2", "Kabila", postnom="Mbuyi")
        cls.ilunga = agent("A/1", "Ilunga")
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def client_for(self, user="Auditeur"):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client

    def test_every_profile_opening_agents_reads_them_others_do_not(self):
        self.assertNotIn("Administrateur système", READERS)
        self.assertEqual(self.client_for(None).get(AGENTS).status_code, 401)
        self.assertEqual(self.client_for(self.nobody).get(AGENTS).status_code, 403)
        for name in GROUPS:
            with self.subTest(name):
                expected = 200 if name in READERS else 403
                self.assertEqual(self.client_for(name).get(AGENTS).status_code, expected)

    def test_list_in_name_order_not_paginated(self):
        rows = self.client_for().get(AGENTS).json()
        self.assertEqual(
            [row["id"] for row in rows], [self.ilunga.pk, self.kabila.pk, self.tshala.pk]
        )

    def test_fields(self):
        row = self.client_for().get(f"{AGENTS}{self.tshala.pk}/").json()
        self.assertEqual(
            {k: v for k, v in row.items() if k not in ("date_creation", "date_modification")},
            {
                "id": self.tshala.pk,
                "matricule": "C/3",
                "nom": "Tshala",
                "postnom": "",
                "prenom": "Marie",
                "sexe": "F",
                "sexe_libelle": "Féminin",
                "date_naissance": "1985-03-14",
                "lieu_naissance": "Kinshasa",
                "nationalite": "Congolaise",
                "cree_par": None,
                "modifie_par": None,
                "coordonnees": None,
                "date_engagement": None,
                "contrats": [],
            },
        )
        self.assertIn("date_creation", row)
        self.assertIn("date_modification", row)

    def test_unknown_id_is_not_found(self):
        self.assertEqual(self.client_for().get(f"{AGENTS}999999/").status_code, 404)

    def test_nobody_writes_not_even_the_editors(self):
        detail = f"{AGENTS}{self.kabila.pk}/"
        for name in ("Gestion de carrière", "Direction RH"):
            with self.subTest(name):
                client = self.client_for(name)
                self.assertEqual(client.post(AGENTS, {}).status_code, 405)
                self.assertEqual(client.put(detail, {}).status_code, 405)
                self.assertEqual(client.patch(detail, {}).status_code, 405)
                self.assertEqual(client.delete(detail).status_code, 405)
        self.assertEqual(Agent.objects.count(), 3)


class CoordonneesApiTests(TestCase):
    """Contact details nested in the agent detail (contact details D18)."""

    @classmethod
    def setUpTestData(cls):
        cls.with_contact = agent("A/1", "Ilunga")
        cls.without = agent("B/2", "Kabeya")
        cls.row = Coordonnees.objects.create(
            agent=cls.with_contact, adresse="Avenue Kasa-Vubu 40", commune="Kalamu",
            ville="Kinshasa", telephone="+243 81 234 5678", courriel="ilunga@example.cd",
            urgence_nom="Ilunga Mujinga", urgence_lien="Épouse", urgence_telephone="0991234567",
        )  # fmt: skip
        cls.reader = member("formation", "Formation")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.reader)

    def test_detail_returns_every_contact_field(self):
        data = self.client.get(f"{AGENTS}{self.with_contact.pk}/").json()["coordonnees"]
        self.assertEqual(
            {k: v for k, v in data.items() if k not in ("date_creation", "date_modification")},
            {
                "adresse": "Avenue Kasa-Vubu 40",
                "commune": "Kalamu",
                "ville": "Kinshasa",
                "telephone": "+243 81 234 5678",
                "telephone_secondaire": "",
                "courriel": "ilunga@example.cd",
                "urgence_nom": "Ilunga Mujinga",
                "urgence_lien": "Épouse",
                "urgence_telephone": "0991234567",
                "cree_par": None,
                "modifie_par": None,
            },
        )
        self.assertIn("date_creation", data)

    def test_detail_without_contact_details_is_null(self):
        response = self.client.get(f"{AGENTS}{self.without.pk}/")
        self.assertIsNone(response.json()["coordonnees"])

    def test_list_has_no_contact_details(self):
        for row in self.client.get(AGENTS).json():
            self.assertNotIn("coordonnees", row)

    def test_detail_runs_a_fixed_number_of_queries(self):
        counts = []
        self.client.get(AGENTS)  # loads and caches the reader's permissions
        for target in (self.with_contact, self.without):
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(self.client.get(f"{AGENTS}{target.pk}/").status_code, 200)
            counts.append(len(queries))
        # The agent with its contact details, then its contracts with their types.
        self.assertEqual(counts, [2, 2])

    def test_contact_details_cannot_be_written(self):
        editor = APIClient()
        editor.force_authenticate(member("carriere", "Gestion de carrière"))
        detail = f"{AGENTS}{self.with_contact.pk}/"
        response = editor.patch(detail, {"coordonnees": {"telephone": "0812345678"}}, format="json")
        self.assertEqual(response.status_code, 405)
        self.row.refresh_from_db()
        self.assertEqual(self.row.telephone, "+243 81 234 5678")


class ContratApiTests(TestCase):
    """Hiring date and contracts in the agent detail (contract D19)."""

    @classmethod
    def setUpTestData(cls):
        cdd = TypeContrat.objects.create(
            code="CDD", nom="Contrat à durée déterminée", duree_determinee=True,
            periode_essai=True, date_ouverture=date(2015, 1, 1),
        )  # fmt: skip
        cdi = TypeContrat.objects.create(
            code="CDI", nom="Contrat à durée indéterminée", duree_determinee=False,
            periode_essai=True, date_ouverture=date(2015, 1, 1),
        )  # fmt: skip
        cls.agent = agent("A/1", "Ilunga")
        # Entered out of order: the API sorts by start date.
        cls.cdi = Contrat.objects.create(agent=cls.agent, type_contrat=cdi,
                                         date_debut=date(2022, 3, 1))  # fmt: skip
        cls.first = Contrat.objects.create(
            agent=cls.agent, type_contrat=cdd, date_debut=date(2020, 3, 1),
            date_fin=date(2021, 2, 28), fin_periode_essai=date(2020, 5, 31),
        )  # fmt: skip
        cls.second = Contrat.objects.create(
            agent=cls.agent, type_contrat=cdd, date_debut=date(2021, 3, 1),
            date_fin=date(2022, 2, 28),
        )  # fmt: skip
        cls.without = agent("B/2", "Kabeya")
        cls.reader = member("formation", "Formation")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.reader)

    def test_contracts_in_date_order_with_every_field(self):
        data = self.client.get(f"{AGENTS}{self.agent.pk}/").json()
        self.assertEqual(data["date_engagement"], "2020-03-01")
        self.assertEqual(
            [row["id"] for row in data["contrats"]], [self.first.pk, self.second.pk, self.cdi.pk]
        )
        first = data["contrats"][0]
        self.assertEqual(
            {k: v for k, v in first.items() if k not in ("date_creation", "date_modification")},
            {
                "id": self.first.pk,
                "type_contrat": self.first.type_contrat_id,
                "type_code": "CDD",
                "type_nom": "Contrat à durée déterminée",
                "date_debut": "2020-03-01",
                "date_fin": "2021-02-28",
                "fin_periode_essai": "2020-05-31",
                "cree_par": None,
                "modifie_par": None,
            },
        )
        self.assertIsNone(data["contrats"][2]["date_fin"])

    def test_agent_without_contract(self):
        data = self.client.get(f"{AGENTS}{self.without.pk}/").json()
        self.assertEqual((data["date_engagement"], data["contrats"]), (None, []))

    def test_list_is_unchanged(self):
        for row in self.client.get(AGENTS).json():
            self.assertNotIn("contrats", row)
            self.assertNotIn("date_engagement", row)

    def test_detail_queries_do_not_grow_with_the_contracts(self):
        self.client.get(AGENTS)  # loads and caches the reader's permissions
        for target in (self.agent, self.without):
            with self.subTest(target=target.matricule), CaptureQueriesContext(connection) as q:
                self.client.get(f"{AGENTS}{target.pk}/")
            self.assertEqual(len(q), 2)

    def test_contracts_cannot_be_written(self):
        editor = APIClient()
        editor.force_authenticate(member("carriere", "Gestion de carrière"))
        response = editor.patch(f"{AGENTS}{self.agent.pk}/", {"contrats": []}, format="json")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.agent.contrats.count(), 3)
