"""Events, their kinds and their required pieces.
See specs/2026-11-22-documents-on-events (D7 to D18)."""

from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.referentiels.models import Evenement as E
from apps.referentiels.models import PieceRequise, TypeContrat

from .evenements import evenements_de, prefetch_evenements
from .models import Affectation, Agent, Classement, Contrat
from .pieces import etat_pieces, etats_pieces, etats_pieces_de, pieces_manquantes
from .test_access import member
from .test_affectations import D2015
from .test_pieces_jointes import Base

D2024 = date(2024, 1, 1)


def requise(evenement, type_document, obligatoire=True, debut=D2015, fin=None):
    return PieceRequise.objects.create(
        evenement=evenement, type_document=type_document, obligatoire=obligatoire,
        date_ouverture=debut, date_fermeture=fin,
    )  # fmt: skip


class Events(Base):
    """CDD from 01/03/2020 (hiring), CDI from 01/06/2022; positions added per test."""

    def kinds(self, agent=None):
        agent = prefetch_evenements(Agent.objects.filter(pk=(agent or self.agent).pk)).get()
        return [(e.modele, e.date, e.evenement) for e in evenements_de(agent)]


class KindTests(Events):
    def test_contracts(self):
        self.assertEqual(
            self.kinds(),
            [("contrat", date(2022, 6, 1), E.RENOUVELLEMENT),
             ("contrat", date(2020, 3, 1), E.ENGAGEMENT)],
        )  # fmt: skip

    def test_assignments(self):
        Affectation.objects.create(agent=self.agent, unite=self.svc, fonction=self.chef,
                                   date_effet=date(2020, 3, 1))  # fmt: skip
        Affectation.objects.create(agent=self.agent, unite=self.drh, fonction=self.chef,
                                   date_effet=date(2022, 6, 1))  # fmt: skip
        kinds = [k for k in self.kinds() if k[0] == "affectation"]
        self.assertEqual(kinds, [("affectation", date(2022, 6, 1), E.MUTATION),
                                 ("affectation", date(2020, 3, 1), None)])  # fmt: skip

    def test_classifications(self):
        for jour, ech in ((date(2020, 3, 1), self.a1e1), (date(2020, 9, 1), self.a1e2),
                          (date(2022, 6, 1), self.a2e1)):  # fmt: skip
            Classement.objects.create(agent=self.agent, echelon=ech, date_effet=jour)
        kinds = [k for k in self.kinds() if k[0] == "classement"]
        self.assertEqual(kinds, [("classement", date(2022, 6, 1), E.PROMOTION),
                                 ("classement", date(2020, 9, 1), E.AVANCEMENT),
                                 ("classement", date(2020, 3, 1), None)])  # fmt: skip

    def test_newest_first_with_contract_before_positions_on_a_day(self):
        Affectation.objects.create(agent=self.agent, unite=self.svc, fonction=self.chef,
                                   date_effet=date(2020, 3, 1))  # fmt: skip
        self.assertEqual([k[0] for k in self.kinds()], ["contrat", "contrat", "affectation"])

    def test_kinds_follow_an_earlier_contract(self):
        cdd = TypeContrat.objects.get(code="CDD")
        Contrat.objects.create(agent=self.agent, type_contrat=cdd, date_debut=date(2018, 1, 1),
                               date_fin=date(2018, 12, 31))  # fmt: skip
        self.assertEqual(
            [k[2] for k in self.kinds()], [E.RENOUVELLEMENT, E.RENOUVELLEMENT, E.ENGAGEMENT]
        )

    def test_protocol_on_the_models(self):
        self.assertEqual(self.cdd.evenement, E.ENGAGEMENT)
        self.assertEqual(self.cdi.evenement, E.RENOUVELLEMENT)
        self.assertEqual(self.cdi.date_evenement, date(2022, 6, 1))

    def test_agent_without_contract_has_no_event(self):
        self.assertEqual(self.kinds(Agent.objects.create(
            matricule="X/1", nom="Sans", sexe="M", date_naissance=date(1990, 1, 1),
            lieu_naissance="Kinshasa")), [])  # fmt: skip


class StatusTests(Events):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        t = cls.types
        requise(E.ENGAGEMENT, t["CTR"])
        requise(E.ENGAGEMENT, t["CNI"])
        requise(E.ENGAGEMENT, t["DIP"])
        requise(E.ENGAGEMENT, t["CJ"], fin=D2024)
        requise(E.RENOUVELLEMENT, t["CTR"])
        requise(E.AVANCEMENT, t["DEC"], obligatoire=False)

    def test_requirements_on_the_event_date(self):
        self.assertEqual(sorted(pieces_manquantes(self.cdd)), ["CJ", "CNI", "CTR", "DIP"])
        self.assertEqual(pieces_manquantes(self.cdi), ["CTR"])
        # A hiring after 2024 does not need the criminal record any more.
        other = self.other
        Contrat.objects.filter(agent=other)  # two contracts, 2020 and 2022
        etat = etat_pieces(Contrat.objects.get(agent=other, date_debut=date(2020, 3, 1)))
        self.assertIn("CJ", [p.code for p in etat.pieces])
        late = Agent.objects.create(
            matricule="X/2",
            nom="Tardif",
            sexe="F",
            date_naissance=date(1995, 1, 1),
            lieu_naissance="Goma",
        )
        late_cdd = Contrat.objects.create(
            agent=late, type_contrat=TypeContrat.objects.get(code="CDI"),
            date_debut=date(2025, 1, 1))  # fmt: skip
        self.assertNotIn("CJ", [p.code for p in etat_pieces(late_cdd).pieces])

    def test_complete_once_every_mandatory_piece_is_attached(self):
        for code in ("CTR", "CNI", "DIP", "CJ"):
            self.joindre(self.doc(code), self.cdd)
        etat = etat_pieces(self.cdd)
        self.assertTrue(etat.complet)
        self.assertEqual(etat.manquantes, [])
        self.assertTrue(all(p.satisfaite for p in etat.pieces))

    def test_optional_never_blocks_and_none_kind_is_complete(self):
        for jour, ech in ((date(2020, 3, 1), self.a1e1), (date(2020, 9, 1), self.a1e2)):
            Classement.objects.create(agent=self.agent, echelon=ech, date_effet=jour)
        avancement = Classement.objects.get(date_effet=date(2020, 9, 1))
        etat = etat_pieces(avancement)
        self.assertTrue(etat.complet)
        self.assertEqual([(p.code, p.obligatoire, p.satisfaite) for p in etat.pieces],
                         [("DEC", False, False)])  # fmt: skip
        inclus = Classement.objects.get(date_effet=date(2020, 3, 1))
        self.assertEqual(etat_pieces(inclus).pieces, [])
        self.assertTrue(etat_pieces(inclus).complet)

    def test_satisfied_by_code_across_a_replaced_type(self):
        contrat = self.doc("CTR")  # uploaded under the old type row
        self.joindre(contrat, self.cdi)
        old = self.types["CTR"]
        for row in PieceRequise.objects.filter(type_document=old):
            row.date_fermeture = date(2022, 1, 1)
            row.save()
        old.date_fermeture = date(2022, 1, 1)
        old.save()
        new = type(old).objects.create(code="CTR", nom="Contrat signé (nouveau)",
                                       date_ouverture=date(2022, 1, 1))  # fmt: skip
        requise(E.RENOUVELLEMENT, new, debut=date(2022, 1, 1))
        self.assertEqual(pieces_manquantes(self.cdi), [])

    def test_retired_document_and_removed_link_stop_counting(self):
        contrat = self.doc("CTR")
        lien = self.joindre(contrat, self.cdi)
        self.assertEqual(pieces_manquantes(self.cdi), [])
        lien.retirer()
        self.assertEqual(pieces_manquantes(self.cdi), ["CTR"])
        self.joindre(contrat, self.cdi)
        contrat.retirer("Scan illisible, à refaire")
        self.assertEqual(pieces_manquantes(self.cdi), ["CTR"])

    def test_other_attached_documents(self):
        self.joindre(self.doc("DEC"), self.cdi)
        etat = etat_pieces(self.cdi)
        self.assertEqual([d.type_document.code for d in etat.autres], ["DEC"])

    def test_confidential_counted_but_listed_to_readers_only(self):
        cni = self.doc("CNI")
        self.joindre(cni, self.cdd)
        formation = member("formation", "Formation")
        etat = etat_pieces(self.cdd, formation)
        piece = next(p for p in etat.pieces if p.code == "CNI")
        self.assertTrue(piece.satisfaite)
        self.assertEqual((piece.documents, piece.confidentielles), ([], 1))
        piece = next(p for p in etat_pieces(self.cdd, self.carriere).pieces if p.code == "CNI")
        self.assertEqual((piece.documents, piece.confidentielles), ([cni], 0))

    def test_fixed_number_of_queries(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                etats_pieces_de(self.agent.pk, self.carriere)
            return len(ctx)

        rows = ((date(2020, 3, 1), self.a1e1), (date(2020, 9, 1), self.a1e2),
                (date(2022, 6, 1), self.a2e1))  # fmt: skip
        for jour, ech in rows[:1]:
            Classement.objects.create(agent=self.agent, echelon=ech, date_effet=jour)
            Affectation.objects.create(agent=self.agent, unite=self.svc, fonction=self.chef,
                                       date_effet=jour)  # fmt: skip
        few = count()
        for jour, ech in rows[1:]:
            Classement.objects.create(agent=self.agent, echelon=ech, date_effet=jour)
            Affectation.objects.create(agent=self.agent, unite=self.svc, fonction=self.chef,
                                       date_effet=jour)  # fmt: skip
        for code in ("CTR", "DIP", "CJ", "DEC"):
            self.joindre(self.doc(code), self.cdd)
            self.joindre(self.doc(code), self.cdi)
        self.assertEqual(count(), few)

    def test_etats_pieces_lists_every_event(self):
        agent = prefetch_evenements(Agent.objects.filter(pk=self.agent.pk)).get()
        etats = etats_pieces(agent)
        self.assertEqual([e.evenement.evenement for e in etats], [E.RENOUVELLEMENT, E.ENGAGEMENT])
        self.assertEqual([e.complet for e in etats], [False, False])
