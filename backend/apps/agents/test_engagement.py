"""Hiring an agent in one go. See specs/2026-11-22-agent-creation-form (D1 to D10)."""

from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import EntreeAudit
from apps.referentiels.models import Categorie, Grade, TypeContrat

from .models import (
    CONTRAT_OVERLAP,
    FIN_OBLIGATOIRE,
    MATRICULE_HELP,
    MATRICULE_TAKEN,
    Affectation,
    Agent,
    Classement,
    Contrat,
    Coordonnees,
)
from .test_access import member
from .test_affectations import D2015
from .test_affectations import Base as PositionBase
from .test_classements import echelon

AGENTS = "/api/agents/"
TABLES = (Agent, Coordonnees, Contrat, Affectation, Classement, EntreeAudit)


class Base(PositionBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cat = Categorie.objects.create(code="A", nom="Cadres", rang=3, date_ouverture=D2015)
        grade = Grade.objects.create(code="A1", nom="Attaché 1", categorie=cat, rang=1,
                                     date_ouverture=D2015)  # fmt: skip
        cls.e1 = echelon(grade, 1)
        cls.closed = echelon(grade, 2, fin=date(2020, 1, 1))
        cls.cdi = TypeContrat.objects.get(code="CDI")
        cls.cdd = TypeContrat.objects.get(code="CDD")
        cls.carriere = member("carriere", "Gestion de carrière")

    def payload(self, **changes):
        data = {
            "matricule": "arptc/0100/2026 ",
            "nom": "Kabongo",
            "postnom": "Mwamba",
            "prenom": "Élodie",
            "sexe": "F",
            "date_naissance": "1995-04-12",
            "lieu_naissance": "Kinshasa",
            "nationalite": "Congolaise",
            "coordonnees": {"adresse": "12, avenue des Aviateurs", "ville": "Kinshasa",
                            "telephone": "+243 810 000 001"},
            "contrat": {"type_contrat": self.cdi.pk, "date_debut": "2026-01-05",
                        "fin_periode_essai": "2026-04-04"},
            "affectation": {"unite": self.svc.pk, "fonction": self.juriste.pk},
            "classement": {"echelon": self.e1.pk},
        }  # fmt: skip
        for key, value in changes.items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **value}
            else:
                data[key] = value
        return data

    def post(self, user=None, **changes):
        client = APIClient()
        if user is not False:
            client.force_authenticate(user or self.carriere)
        return client.post(AGENTS, self.payload(**changes), format="json")

    def counts(self):
        return [model.objects.count() for model in TABLES]


class HiringTests(Base):
    def test_full_hiring_creates_five_rows_dated_on_the_start(self):
        response = self.post()
        self.assertEqual(response.status_code, 201, response.json())
        body = response.json()
        agent = Agent.objects.get(pk=body["id"])
        self.assertEqual(agent.matricule, "ARPTC/0100/2026")
        self.assertEqual(agent.coordonnees.ville, "Kinshasa")
        contrat = agent.contrats.get()
        self.assertEqual((contrat.type_contrat, contrat.date_debut), (self.cdi, date(2026, 1, 5)))
        self.assertEqual(agent.affectations.get().date_effet, date(2026, 1, 5))
        self.assertEqual(agent.classements.get().date_effet, date(2026, 1, 5))
        self.assertEqual(body["date_engagement"], "2026-01-05")
        self.assertEqual(body["coordonnees"]["ville"], "Kinshasa")

    def test_every_row_authored_and_audited(self):
        agent = Agent.objects.get(pk=self.post().json()["id"])
        rows = [agent, agent.coordonnees, agent.contrats.get(), agent.affectations.get(),
                agent.classements.get()]  # fmt: skip
        for row in rows:
            with self.subTest(type(row).__name__):
                self.assertEqual(row.cree_par, self.carriere)
                entry = EntreeAudit.objects.get(table__model=row._meta.model_name, objet_id=row.pk)
                self.assertEqual(entry.auteur, self.carriere)

    def test_without_contact_details(self):
        response = self.post(coordonnees=None)
        self.assertEqual(response.status_code, 201)
        self.assertFalse(Coordonnees.objects.exists())
        blank = self.post(
            matricule="X/2", coordonnees={"adresse": "", "ville": "  ", "telephone": ""}
        )
        self.assertEqual(blank.status_code, 201, blank.json())
        self.assertFalse(Coordonnees.objects.exists())


class RefusalTests(Base):
    def assertRefused(self, response, expected):
        self.assertEqual(response.status_code, 400)
        body = response.json()
        for path, message in expected:
            node = body
            for key in path:
                node = node[key]
            self.assertIn(message, node, body)

    def test_matricule_taken_or_malformed(self):
        self.post()
        self.assertRefused(self.post(), [(("matricule",), MATRICULE_TAKEN)])
        self.assertRefused(self.post(matricule="ARPTC 01"), [(("matricule",), MATRICULE_HELP)])

    def test_contract_rules(self):
        response = self.post(contrat={"type_contrat": self.cdd.pk, "fin_periode_essai": None})
        self.assertRefused(response, [(("contrat", "date_fin"), FIN_OBLIGATOIRE)])

    def test_closed_echelon_and_unit(self):
        self.bur.date_fermeture = date(2025, 1, 1)
        self.bur.save()
        response = self.post(affectation={"unite": self.bur.pk},
                             classement={"echelon": self.closed.pk})  # fmt: skip
        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("unite", body["affectation"])
        self.assertIn("echelon", body["classement"])

    def test_errors_of_several_sections_together(self):
        self.post()
        response = self.post(contrat={"type_contrat": self.cdd.pk, "fin_periode_essai": None},
                             classement={"echelon": self.closed.pk})  # fmt: skip
        body = response.json()
        self.assertEqual(set(body), {"matricule", "contrat", "classement"})

    def test_missing_sections(self):
        data = self.payload()
        for key in ("contrat", "affectation", "classement"):
            data.pop(key)
        client = APIClient()
        client.force_authenticate(self.carriere)
        body = client.post(AGENTS, data, format="json").json()
        self.assertEqual({"contrat", "affectation", "classement"} <= set(body), True)

    def test_a_refusal_in_the_last_section_leaves_nothing(self):
        before = self.counts()
        response = self.post(classement={"echelon": self.closed.pk})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(response.json()), ["classement"])
        self.assertEqual(self.counts(), before)

    def test_contract_overlap_message_is_the_models(self):
        # The new agent has no contract yet, so no overlap: the model's message exists all the same.
        self.assertTrue(CONTRAT_OVERLAP)


class AccessTests(Base):
    def test_who_may_hire(self):
        self.assertEqual(self.post(user=False).status_code, 401)
        for n, group in enumerate(["Rémunération", "Formation", "Auditeur", "Direction RH",
                                   "Administrateur système"]):  # fmt: skip
            with self.subTest(group):
                self.assertEqual(self.post(user=member(f"u{n}", group)).status_code, 403)
        chef = member("chef", "Chef de service — Gestion de carrière")
        self.assertEqual(self.post(user=chef).status_code, 201)

    def test_detail_stays_read_only(self):
        agent_id = self.post().json()["id"]
        client = APIClient()
        client.force_authenticate(self.carriere)
        for method in ("put", "patch", "delete"):
            self.assertEqual(getattr(client, method)(f"{AGENTS}{agent_id}/").status_code, 405)


class EmptySuggestionTests(TestCase):
    def test_first_suggestion_without_any_agent(self):
        from .engagement import matricule_suivant

        self.assertEqual(matricule_suivant(2026), "ARPTC/0001/2026")


class SuggestionAndDuplicateTests(Base):
    def get(self, url, user=None):
        client = APIClient()
        client.force_authenticate(user or self.carriere)
        return client.get(url)

    def test_suggestion(self):
        url = f"{AGENTS}matricule-suivant/?annee=2026"
        # The fixture holds ARPTC/0001/2020 and ARPTC/0002/2020.
        self.assertEqual(self.get(url).json(), {"matricule": "ARPTC/0003/2026"})
        for matricule in ("ARPTC/0012/2024", "ARPTC/0007/2015", "CHARGE/09999", "ARPTC-0500"):
            Agent.objects.create(matricule=matricule, nom="X", sexe="M",
                                 date_naissance=date(1990, 1, 1), lieu_naissance="K")  # fmt: skip
        self.assertEqual(self.get(url).json(), {"matricule": "ARPTC/0013/2026"})
        self.assertEqual(self.get(f"{AGENTS}matricule-suivant/").status_code, 400)

    def test_duplicates(self):
        self.post()  # Kabongo Élodie, 12/04/1995
        url = f"{AGENTS}doublons/?nom=KABONGO&date_naissance=1995-04-12"
        rows = self.get(url).json()
        self.assertEqual([r["matricule"] for r in rows], ["ARPTC/0100/2026"])
        self.assertEqual(len(self.get(url + "&prenom=elodie").json()), 1)
        self.assertEqual(self.get(url + "&prenom=Marie").json(), [])
        self.assertEqual(
            self.get(f"{AGENTS}doublons/?nom=Kabongo&date_naissance=1995-04-13").json(), []
        )
        for n in range(12):
            Agent.objects.create(matricule=f"D/{n}", nom="Kabongo", sexe="M",
                                 date_naissance=date(1995, 4, 12), lieu_naissance="K")  # fmt: skip
        self.assertEqual(len(self.get(url).json()), 10)
        self.assertEqual(self.get(f"{AGENTS}doublons/?nom=Kabongo").status_code, 400)

    def test_both_need_add_agent(self):
        formation = member("formation", "Formation")
        for url in (f"{AGENTS}matricule-suivant/?annee=2026",
                    f"{AGENTS}doublons/?nom=X&date_naissance=1990-01-01"):  # fmt: skip
            self.assertEqual(self.get(url, formation).status_code, 403)
