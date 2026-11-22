"""The events API. See specs/2026-11-22-documents-on-events (D18 to D22)."""

from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.referentiels.models import Evenement as E

from .evenement_views import PIECE_INTROUVABLE
from .models import LIEN_DOUBLON, LIEN_PIECE_RETIREE, Affectation, Classement
from .test_access import member
from .test_evenements import requise
from .test_pieces_jointes import Base

FIELDS = {"cle", "modele", "id", "evenement", "evenement_libelle", "date", "libelle", "complet",
          "manquantes", "pieces", "autres", "autres_confidentielles"}  # fmt: skip


class ApiBase(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        t = cls.types
        requise(E.ENGAGEMENT, t["CTR"])
        requise(E.ENGAGEMENT, t["CNI"])
        requise(E.ENGAGEMENT, t["DIP"], obligatoire=False)
        requise(E.RENOUVELLEMENT, t["CTR"])
        cls.formation = member("formation", "Formation")
        cls.personnel = member("personnel", "Administration du personnel")
        cls.admin = member("admin", "Administrateur système")

    def api(self, user):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client

    def url(self, suffix="", agent=None):
        return f"/api/agents/{(agent or self.agent).pk}/evenements/{suffix}"

    def joindre_api(self, document, evenement="contrat", objet=None, user=None):
        objet = objet or self.cdd
        return self.api(user or self.carriere).post(
            self.url(f"{evenement}/{objet.pk}/pieces/"), {"document": document.pk}, format="json"
        )


class ListTests(ApiBase):
    def test_fields_and_order(self):
        rows = self.api(self.formation).get(self.url()).json()
        self.assertEqual(
            [r["cle"] for r in rows], [f"contrat-{self.cdi.pk}", f"contrat-{self.cdd.pk}"]
        )
        engagement = rows[1]
        self.assertEqual(set(engagement), FIELDS)
        self.assertEqual(engagement["evenement"], "engagement")
        self.assertEqual(engagement["evenement_libelle"], "Engagement")
        self.assertEqual(engagement["date"], "2020-03-01")
        self.assertFalse(engagement["complet"])
        self.assertEqual(sorted(engagement["manquantes"]), ["CNI", "CTR"])
        self.assertEqual(
            [(p["code"], p["obligatoire"], p["satisfaite"]) for p in engagement["pieces"]],
            [("CTR", True, False), ("CNI", True, False), ("DIP", False, False)],
        )

    def test_confidential_counted_and_hidden(self):
        cni = self.doc("CNI", nom="carte.pdf")
        self.joindre(cni, self.cdd)
        rows = self.api(self.formation).get(self.url()).json()
        piece = next(p for p in rows[1]["pieces"] if p["code"] == "CNI")
        self.assertTrue(piece["satisfaite"])
        self.assertEqual((piece["documents"], piece["confidentielles"]), ([], 1))
        rows = self.api(self.carriere).get(self.url()).json()
        piece = next(p for p in rows[1]["pieces"] if p["code"] == "CNI")
        self.assertEqual([d["nom_original"] for d in piece["documents"]], ["carte.pdf"])
        self.assertIsNotNone(piece["documents"][0]["lien"])

    def test_fixed_number_of_queries(self):
        client = self.api(self.carriere)
        client.get(self.url())
        Affectation.objects.create(agent=self.agent, unite=self.svc, fonction=self.chef,
                                   date_effet=date(2020, 3, 1))  # fmt: skip
        Classement.objects.create(agent=self.agent, echelon=self.a1e1, date_effet=date(2020, 3, 1))
        with CaptureQueriesContext(connection) as few:
            client.get(self.url())
        for jour, ech in ((date(2020, 9, 1), self.a1e2), (date(2022, 6, 1), self.a2e1)):
            Classement.objects.create(agent=self.agent, echelon=ech, date_effet=jour)
            Affectation.objects.create(agent=self.agent, unite=self.drh, fonction=self.chef,
                                       date_effet=jour)  # fmt: skip
        for code in ("CTR", "CNI", "DIP", "DEC"):
            self.joindre(self.doc(code), self.cdd)
            self.joindre(self.doc(code), self.cdi)
        with CaptureQueriesContext(connection) as many:
            client.get(self.url())
        self.assertEqual(len(few), len(many))


class AttachTests(ApiBase):
    def test_attach_returns_the_event_with_its_status(self):
        response = self.joindre_api(self.doc("CTR"), objet=self.cdi)
        self.assertEqual(response.status_code, 201, response.json())
        self.assertTrue(response.json()["complet"])
        self.assertEqual(response.json()["cle"], f"contrat-{self.cdi.pk}")

    def test_administration_du_personnel_attaches_too(self):
        response = self.joindre_api(self.doc("CTR"), objet=self.cdi, user=self.personnel)
        self.assertEqual(response.status_code, 201)

    def test_refusals_on_document(self):
        contrat = self.doc("CTR")
        self.joindre_api(contrat)
        self.assertEqual(self.joindre_api(contrat).json()["document"], [LIEN_DOUBLON])
        retired = self.doc("DIP")
        retired.retirer("Scan illisible, à refaire")
        self.assertEqual(self.joindre_api(retired).json()["document"], [LIEN_PIECE_RETIREE])
        other = self.doc("CTR", agent=self.other)
        self.assertEqual(self.joindre_api(other).json()["document"], [PIECE_INTROUVABLE])
        # A confidential document the user cannot read is not found either.
        cni = self.doc("CNI")
        response = self.joindre_api(cni, user=self.personnel)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["document"], [PIECE_INTROUVABLE])

    def test_remove_link(self):
        contrat = self.doc("CTR")
        lien = self.joindre_api(contrat, objet=self.cdi).json()["pieces"][0]["documents"][0]["lien"]
        url = self.url(f"contrat/{self.cdi.pk}/pieces/{lien}/retrait/")
        response = self.api(self.carriere).post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["complet"])
        self.assertEqual(self.api(self.carriere).post(url).status_code, 400)

    def test_event_of_another_agent_or_unknown_model_404(self):
        other_contract = self.other.contrats.first()
        document = self.doc("CTR")
        self.assertEqual(self.joindre_api(document, objet=other_contract).status_code, 404)
        response = self.api(self.carriere).post(
            self.url(f"agent/{self.agent.pk}/pieces/"), {"document": document.pk}, format="json"
        )
        self.assertEqual(response.status_code, 404)


class AccessTests(ApiBase):
    def test_anonymous_401_and_no_agents_403(self):
        self.assertEqual(self.api(None).get(self.url()).status_code, 401)
        for user in (self.admin, member("personne")):
            self.assertEqual(self.api(user).get(self.url()).status_code, 403)
            self.assertEqual(self.api(user).get("/api/agents/999999/evenements/").status_code, 403)

    def test_unknown_agent_404_for_a_reader(self):
        self.assertEqual(
            self.api(self.formation).get("/api/agents/999999/evenements/").status_code, 404
        )

    def test_readers_cannot_attach_or_remove(self):
        lien = self.joindre(self.doc("CTR"), self.cdd)
        for user in (self.formation, member("direction", "Direction RH")):
            self.assertEqual(self.joindre_api(self.doc("DIP"), user=user).status_code, 403)
            url = self.url(f"contrat/{self.cdd.pk}/pieces/{lien.pk}/retrait/")
            self.assertEqual(self.api(user).post(url).status_code, 403)

    def test_other_methods_405(self):
        client = self.api(self.carriere)
        for method in ("post", "put", "patch", "delete"):
            self.assertEqual(getattr(client, method)(self.url()).status_code, 405)
        for method in ("get", "put", "delete"):
            response = getattr(client, method)(self.url(f"contrat/{self.cdd.pk}/pieces/"))
            self.assertEqual(response.status_code, 405)
