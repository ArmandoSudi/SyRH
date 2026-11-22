"""GET /api/agents/ (agent identity D13, D18, D19; contact details D18; contract D19;
position history D19, D20; bank account D15, D18)."""

from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.roles import GROUPS
from apps.referentiels.models import (
    Banque,
    Categorie,
    Echelon,
    Fonction,
    Grade,
    Site,
    TypeContrat,
    UniteOrganisationnelle,
)

from .models import Affectation, Agent, Classement, CompteBancaire, Contrat, Coordonnees

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

    def test_list_in_name_order(self):
        rows = self.client_for().get(AGENTS).json()["results"]
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
                "statut": "sans_contrat",
                "statut_libelle": "Sans contrat",
                "affectation_actuelle": None,
                "classement_actuel": None,
                "cree_par": None,
                "modifie_par": None,
                "coordonnees": None,
                "date_engagement": None,
                "contrats": [],
                "affectations": [],
                "classements": [],
            },
        )
        self.assertIn("date_creation", row)
        self.assertIn("date_modification", row)

    def test_unknown_id_is_not_found(self):
        self.assertEqual(self.client_for().get(f"{AGENTS}999999/").status_code, 404)

    def test_nobody_writes_an_agent_not_even_the_editors(self):
        # POST /api/agents/ hires (agent creation form D1); an agent itself stays read-only (D10).
        detail = f"{AGENTS}{self.kabila.pk}/"
        for name in ("Gestion de carrière", "Direction RH"):
            with self.subTest(name):
                client = self.client_for(name)
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
        for row in self.client.get(AGENTS).json()["results"]:
            self.assertNotIn("coordonnees", row)

    def test_detail_runs_a_fixed_number_of_queries(self):
        counts = []
        self.client.get(AGENTS)  # loads and caches the reader's permissions
        for target in (self.with_contact, self.without):
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(self.client.get(f"{AGENTS}{target.pk}/").status_code, 200)
            counts.append(len(queries))
        # The agent with its contact details, then its contracts with their types,
        # its assignments and its classifications.
        self.assertEqual(counts, [4, 4])

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
        for row in self.client.get(AGENTS).json()["results"]:
            self.assertNotIn("contrats", row)
            self.assertNotIn("date_engagement", row)

    def test_detail_queries_do_not_grow_with_the_contracts(self):
        self.client.get(AGENTS)  # loads and caches the reader's permissions
        for target in (self.agent, self.without):
            with self.subTest(target=target.matricule), CaptureQueriesContext(connection) as q:
                self.client.get(f"{AGENTS}{target.pk}/")
            self.assertEqual(len(q), 4)

    def test_contracts_cannot_be_written(self):
        editor = APIClient()
        editor.force_authenticate(member("carriere", "Gestion de carrière"))
        response = editor.patch(f"{AGENTS}{self.agent.pk}/", {"contrats": []}, format="json")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.agent.contrats.count(), 3)


def frozen_today(day):
    """Freeze the view's today (position history D20)."""
    return mock.patch("apps.agents.views.timezone.localdate", return_value=day)


class PositionApiTests(TestCase):
    """Assignments and classifications in the agent detail and the current ones in
    the list (position history D19, D20)."""

    @classmethod
    def setUpTestData(cls):
        d2015 = date(2015, 1, 1)
        site = Site.objects.create(code="KIN", nom="Kinshasa", ville="Kinshasa", siege=True)
        cls.drh = UniteOrganisationnelle.objects.create(
            code="DRH", nom="Direction des ressources humaines", type="direction", site=site,
            date_ouverture=d2015,
        )  # fmt: skip
        dep = UniteOrganisationnelle.objects.create(
            code="DGC", nom="Département carrière", type="departement", parent=cls.drh,
            site=site, date_ouverture=d2015,
        )  # fmt: skip
        cls.scar = UniteOrganisationnelle.objects.create(
            code="SCAR", nom="Service carrière", type="service", parent=dep, site=site,
            date_ouverture=d2015,
        )  # fmt: skip
        cls.juriste = Fonction.objects.create(
            code="JUR", nom="Juriste", nature="execution", date_ouverture=d2015
        )
        cls.chef = Fonction.objects.create(
            code="CS", nom="Chef de service", nature="responsabilite", date_ouverture=d2015
        )
        cat = Categorie.objects.create(code="A", nom="Cadres", rang=3, date_ouverture=d2015)
        cls.a2 = Grade.objects.create(
            code="A2", nom="Attaché", categorie=cat, rang=2, date_ouverture=d2015
        )
        cls.a1 = Grade.objects.create(
            code="A1", nom="Chef de bureau", categorie=cat, rang=3, date_ouverture=d2015
        )
        cls.a2e1 = Echelon.objects.create(grade=cls.a2, numero=1, date_ouverture=d2015)
        cls.a1e1 = Echelon.objects.create(grade=cls.a1, numero=1, date_ouverture=d2015)
        cdi = TypeContrat.objects.create(
            code="CDI", nom="CDI", duree_determinee=False, periode_essai=True,
            date_ouverture=d2015,
        )  # fmt: skip
        cls.agent = agent("A/1", "Ilunga")
        Contrat.objects.create(agent=cls.agent, type_contrat=cdi, date_debut=date(2020, 3, 1))
        # Entered out of order: the API sorts by effective date.
        cls.chef_row = Affectation.objects.create(
            agent=cls.agent, unite=cls.scar, fonction=cls.chef, date_effet=date(2023, 1, 1)
        )
        cls.first = Affectation.objects.create(
            agent=cls.agent, unite=cls.drh, fonction=cls.juriste, date_effet=date(2020, 3, 1)
        )
        cls.debut = Classement.objects.create(
            agent=cls.agent, echelon=cls.a2e1, date_effet=date(2020, 3, 1)
        )
        cls.promotion = Classement.objects.create(
            agent=cls.agent, echelon=cls.a1e1, date_effet=date(2025, 1, 1)
        )
        cls.without = agent("B/2", "Kabeya")
        cls.reader = member("formation", "Formation")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.reader)

    def detail(self, target=None):
        return self.client.get(f"{AGENTS}{(target or self.agent).pk}/").json()

    def current(self, day, target=None):
        with frozen_today(day):
            rows = self.client.get(AGENTS).json()["results"]
        return next(row for row in rows if row["id"] == (target or self.agent).pk)

    def test_histories_in_date_order_with_every_field(self):
        data = self.detail()
        self.assertEqual(
            [row["id"] for row in data["affectations"]], [self.first.pk, self.chef_row.pk]
        )
        self.assertEqual(
            [row["id"] for row in data["classements"]], [self.debut.pk, self.promotion.pk]
        )
        strip = {"date_creation", "date_modification"}
        self.assertEqual(
            {k: v for k, v in data["affectations"][1].items() if k not in strip},
            {
                "id": self.chef_row.pk,
                "unite": self.scar.pk,
                "unite_code": "SCAR",
                "unite_nom": "Service carrière",
                "unite_type": "service",
                "fonction": self.chef.pk,
                "fonction_code": "CS",
                "fonction_nom": "Chef de service",
                "date_effet": "2023-01-01",
                "cree_par": None,
                "modifie_par": None,
            },
        )
        self.assertEqual(
            {k: v for k, v in data["classements"][0].items() if k not in strip},
            {
                "id": self.debut.pk,
                "echelon": self.a2e1.pk,
                "echelon_numero": 1,
                "grade": self.a2.pk,
                "grade_code": "A2",
                "grade_nom": "Attaché",
                "categorie_code": "A",
                "date_effet": "2020-03-01",
                "cree_par": None,
                "modifie_par": None,
            },
        )

    def test_agent_without_rows(self):
        data = self.detail(self.without)
        self.assertEqual((data["affectations"], data["classements"]), ([], []))

    def test_list_shows_the_rows_in_force_today(self):
        row = self.current(date(2024, 6, 1))
        self.assertEqual(
            row["affectation_actuelle"],
            {
                "id": self.chef_row.pk,
                "unite": self.scar.pk,
                "unite_code": "SCAR",
                "unite_nom": "Service carrière",
                "unite_type": "service",
                "fonction": self.chef.pk,
                "fonction_code": "CS",
                "fonction_nom": "Chef de service",
                "date_effet": "2023-01-01",
            },
        )
        # The promotion of 01/01/2025 is not current yet.
        self.assertEqual(row["classement_actuel"]["id"], self.debut.pk)
        self.assertNotIn("cree_par", row["classement_actuel"])
        self.assertNotIn("affectations", row)

    def test_a_row_dated_today_is_current_a_future_one_is_not(self):
        self.assertEqual(self.current(date(2025, 1, 1))["classement_actuel"]["id"],
                         self.promotion.pk)  # fmt: skip
        self.assertEqual(self.current(date(2024, 12, 31))["classement_actuel"]["id"],
                         self.debut.pk)  # fmt: skip
        before = self.current(date(2020, 2, 29))
        self.assertEqual((before["affectation_actuelle"], before["classement_actuel"]),
                         (None, None))  # fmt: skip

    def test_agent_without_rows_has_null_current_rows(self):
        row = self.current(date(2024, 6, 1), self.without)
        self.assertEqual((row["affectation_actuelle"], row["classement_actuel"]), (None, None))

    def test_detail_shows_the_current_rows_too(self):
        with frozen_today(date(2024, 6, 1)):
            data = self.detail()
        self.assertEqual(data["affectation_actuelle"]["id"], self.chef_row.pk)
        self.assertEqual(data["classement_actuel"]["id"], self.debut.pk)

    def test_list_queries_do_not_grow_with_the_agents(self):
        self.client.get(AGENTS)  # loads and caches the reader's permissions
        with CaptureQueriesContext(connection) as few:
            self.client.get(AGENTS)
        cdi = TypeContrat.objects.get(code="CDI")
        for n in range(8):
            other = agent(f"C/{n}", f"Agent {n}")
            Contrat.objects.create(agent=other, type_contrat=cdi, date_debut=date(2020, 3, 1))
            Affectation.objects.create(
                agent=other, unite=self.drh, fonction=self.juriste, date_effet=date(2020, 3, 1)
            )
            Classement.objects.create(agent=other, echelon=self.a2e1, date_effet=date(2020, 3, 1))
        with CaptureQueriesContext(connection) as many:
            rows = self.client.get(AGENTS).json()["results"]
        self.assertEqual(len(rows), 10)
        # The count, the page of agents, their assignments and their classifications.
        self.assertEqual((len(few), len(many)), (4, 4))

    def test_histories_cannot_be_written(self):
        editor = APIClient()
        editor.force_authenticate(member("carriere", "Gestion de carrière"))
        response = editor.patch(
            f"{AGENTS}{self.agent.pk}/",
            {"affectations": [], "classements": []},
            format="json",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual((self.agent.affectations.count(), self.agent.classements.count()), (2, 2))


PAIE_READERS = {name for name, (_, modules) in GROUPS.items() if {"agents", "paie"} <= set(modules)}


class CompteBancaireApiTests(TestCase):
    """GET /api/agents/<id>/comptes-bancaires/, for the pay profiles only (bank account
    D15, D18)."""

    @classmethod
    def setUpTestData(cls):
        d2015 = date(2015, 1, 1)
        cls.bcf = Banque.objects.create(code="BCF", nom="Banque du Fleuve", date_ouverture=d2015)
        cls.bik = Banque.objects.create(code="BIK", nom="Banque de Kinshasa", date_ouverture=d2015)
        cls.agent = agent("A/1", "Ilunga")
        cls.without = agent("B/2", "Kabila")
        # Entered out of order: the endpoint sorts by date.
        cls.future = CompteBancaire.objects.create(
            agent=cls.agent, banque=cls.bik, numero="BIK-777", date_effet=date(2025, 1, 1)
        )
        cls.first = CompteBancaire.objects.create(
            agent=cls.agent, banque=cls.bcf, numero="05100 0001234", date_effet=date(2020, 3, 1)
        )
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def url(self, agent=None):
        return f"{AGENTS}{(agent or self.agent).pk}/comptes-bancaires/"

    def client_for(self, user="Rémunération"):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client

    def get(self, day=date(2024, 6, 1), agent=None, user="Rémunération"):
        with frozen_today(day):
            response = self.client_for(user).get(self.url(agent))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_only_the_pay_profiles_read_accounts(self):
        self.assertEqual(
            PAIE_READERS, {"Rémunération", "Chef de service — Rémunération", "Direction RH"}
        )
        self.assertEqual(self.client_for(None).get(self.url()).status_code, 401)
        self.assertEqual(self.client_for(self.nobody).get(self.url()).status_code, 403)
        for name in GROUPS:
            with self.subTest(name):
                expected = 200 if name in PAIE_READERS else 403
                self.assertEqual(self.client_for(name).get(self.url()).status_code, expected)

    def test_accounts_in_date_order_with_every_field(self):
        data = self.get()
        self.assertEqual([row["id"] for row in data["comptes"]], [self.first.pk, self.future.pk])
        row = data["comptes"][0]
        self.assertEqual(
            {k: v for k, v in row.items() if k not in ("date_creation", "date_modification")},
            {
                "id": self.first.pk, "banque": self.bcf.pk, "banque_code": "BCF",
                "banque_nom": "Banque du Fleuve", "numero": "05100 0001234",
                "date_effet": "2020-03-01", "cree_par": None, "modifie_par": None,
            },
        )  # fmt: skip
        self.assertEqual(
            data["compte_actuel"],
            {
                "id": self.first.pk, "banque": self.bcf.pk, "banque_code": "BCF",
                "banque_nom": "Banque du Fleuve", "numero": "05100 0001234",
                "date_effet": "2020-03-01",
            },
        )  # fmt: skip

    def test_a_row_dated_today_is_current_a_future_one_is_not(self):
        self.assertEqual(self.get(date(2025, 1, 1))["compte_actuel"]["id"], self.future.pk)
        self.assertEqual(self.get(date(2024, 12, 31))["compte_actuel"]["id"], self.first.pk)
        self.assertIsNone(self.get(date(2020, 2, 29))["compte_actuel"])

    def test_agent_without_accounts(self):
        self.assertEqual(self.get(agent=self.without), {"comptes": [], "compte_actuel": None})

    def test_unknown_agent_is_not_found_for_a_pay_reader_only(self):
        url = f"{AGENTS}999999/comptes-bancaires/"
        self.assertEqual(self.client_for().get(url).status_code, 404)
        self.assertEqual(self.client_for("Gestion de carrière").get(url).status_code, 403)

    def test_nobody_writes(self):
        for name in ("Rémunération", "Direction RH"):
            with self.subTest(name):
                client = self.client_for(name)
                for method in (client.post, client.put, client.patch, client.delete):
                    self.assertEqual(method(self.url(), {}, format="json").status_code, 405)
        self.assertEqual(CompteBancaire.objects.count(), 2)

    def test_fixed_number_of_queries(self):
        client = self.client_for()
        client.get(self.url())  # loads and caches the reader's permissions
        with self.assertNumQueries(2):  # the agent, then their accounts with the banks
            client.get(self.url())

    def test_list_and_detail_carry_no_account(self):
        client = self.client_for("Direction RH")
        for url in (AGENTS, f"{AGENTS}{self.agent.pk}/"):
            with self.subTest(url):
                body = client.get(url).content.decode()
                for leaked in ("05100 0001234", "BIK-777", "compte"):
                    self.assertNotIn(leaked, body)
