"""Documents attached to events. See specs/2026-11-22-documents-on-events (D1 to D6)."""

from datetime import date

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from apps.audit.models import EntreeAudit
from apps.referentiels.models import Categorie, Cle, Grade, Parametre, TypeDocument

from .documents import create_document
from .models import (
    LIEN_AUTRE_AGENT,
    LIEN_DEJA_RETIRE,
    LIEN_DOUBLON,
    LIEN_EVENEMENT_INCONNU,
    LIEN_FIXE,
    LIEN_PIECE_RETIREE,
    Contrat,
    PieceJointe,
)
from .test_access import member
from .test_affectations import D2015, errors_of
from .test_affectations import Base as PositionBase
from .test_classements import echelon


class Base(PositionBase):
    """The agent of the position tests (CDD 2020, CDI 2022), the document types of the
    demo, and a few documents of their file."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Parametre.objects.create(cle=Cle.TAILLE_MAX_PIECE, valeur=10, date_ouverture=D2015)
        cat = Categorie.objects.create(code="A", nom="Cadres", rang=3, date_ouverture=D2015)
        cls.a1 = Grade.objects.create(code="A1", nom="Attaché 1", categorie=cat, rang=1,
                                      date_ouverture=D2015)  # fmt: skip
        cls.a2 = Grade.objects.create(code="A2", nom="Attaché 2", categorie=cat, rang=2,
                                      date_ouverture=D2015)  # fmt: skip
        cls.a1e1, cls.a1e2 = echelon(cls.a1, 1), echelon(cls.a1, 2)
        cls.a2e1 = echelon(cls.a2, 1)
        types = {}
        for code, nom in (("CTR", "Contrat signé"), ("CNI", "Pièce d'identité"),
                          ("DIP", "Diplôme"), ("CJ", "Casier judiciaire"),
                          ("DEC", "Décision")):  # fmt: skip
            types[code] = TypeDocument.objects.create(code=code, nom=nom, date_ouverture=D2015)
        cls.types = types
        types["CNI"].confidentiel = True
        types["CNI"].save()
        types["CNI"].groupes_autorises.set([Group.objects.get(name="Gestion de carrière")])
        cls.carriere = member("carriere", "Gestion de carrière")
        cls.cdd = Contrat.objects.get(agent=cls.agent, date_debut=date(2020, 3, 1))
        cls.cdi = Contrat.objects.get(agent=cls.agent, date_debut=date(2022, 6, 1))
        cls.serial = 0

    @classmethod
    def doc(cls, code, agent=None, nom=None):
        cls.serial += 1
        content = b"%PDF-1.4 " + str(cls.serial).encode() + code.encode()
        return create_document(
            agent or cls.agent,
            cls.types[code],
            SimpleUploadedFile(nom or f"{code}-{cls.serial}.pdf", content),
        )

    def joindre(self, document, evenement, auteur=None):
        lien = PieceJointe(document=document, evenement_objet=evenement, cree_par=auteur,
                           modifie_par=auteur)  # fmt: skip
        lien.save()
        return lien


class PieceJointeTests(Base):
    def test_attach_and_label(self):
        contrat = self.doc("CTR", nom="contrat.pdf")
        lien = self.joindre(contrat, self.cdd)
        self.assertEqual(lien.evenement_objet, self.cdd)
        self.assertTrue(lien.actif)
        self.assertEqual(str(lien), f"CTR — contrat.pdf → {self.cdd}")
        self.assertEqual(list(self.cdd.pieces_jointes.all()), [lien])

    def test_one_document_justifies_several_events(self):
        decision = self.doc("DEC")
        self.joindre(decision, self.cdd)
        self.joindre(decision, self.cdi)
        self.assertEqual(decision.liens.count(), 2)

    def test_duplicate_active_link_refused(self):
        contrat = self.doc("CTR")
        self.joindre(contrat, self.cdd)
        errors = errors_of(lambda: self.joindre(contrat, self.cdd))
        self.assertEqual(errors, {"document": [LIEN_DOUBLON]})

    def test_duplicate_refused_by_the_database(self):
        contrat = self.doc("CTR")
        lien = self.joindre(contrat, self.cdd)
        copy = PieceJointe(document=contrat, content_type=lien.content_type, objet_id=lien.objet_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PieceJointe._base_manager.bulk_create([copy])

    def test_attach_again_after_removal(self):
        contrat = self.doc("CTR")
        self.joindre(contrat, self.cdd).retirer()
        self.joindre(contrat, self.cdd)
        self.assertEqual(PieceJointe.objects.filter(document=contrat).count(), 2)

    def test_other_agent_and_retired_document_refused(self):
        autre = self.doc("CTR", agent=self.other)
        self.assertEqual(
            errors_of(lambda: self.joindre(autre, self.cdd)), {"document": [LIEN_AUTRE_AGENT]}
        )
        retire = self.doc("DIP")
        retire.retirer("Scan illisible, à refaire")
        self.assertEqual(
            errors_of(lambda: self.joindre(retire, self.cdd)), {"document": [LIEN_PIECE_RETIREE]}
        )

    def test_event_of_an_unknown_model_refused(self):
        contrat = self.doc("CTR")
        lien = PieceJointe(
            document=contrat,
            content_type=ContentType.objects.get_for_model(self.agent),
            objet_id=self.agent.pk,
        )
        self.assertEqual(errors_of(lien.save), {"content_type": [LIEN_EVENEMENT_INCONNU]})

    def test_link_fixed_once_saved(self):
        lien = self.joindre(self.doc("CTR"), self.cdd)
        lien.objet_id = self.cdi.pk
        self.assertEqual(errors_of(lien.save), {"objet": [LIEN_FIXE]})

    def test_removal_once_and_never_deleted(self):
        lien = self.joindre(self.doc("CTR"), self.cdd)
        lien.retirer(auteur=self.carriere)
        lien.refresh_from_db()
        self.assertFalse(lien.actif)
        self.assertEqual(lien.retire_par, self.carriere)
        self.assertEqual(errors_of(lien.retirer), {"lien": [LIEN_DEJA_RETIRE]})
        with self.assertRaises(PermissionError):
            lien.delete()
        self.assertNotIn("delete", PieceJointe._meta.default_permissions)

    def test_audit_of_attach_and_removal(self):
        lien = self.joindre(self.doc("CTR", nom="contrat.pdf"), self.cdd, auteur=self.carriere)
        lien.retirer(auteur=self.carriere)
        entries = EntreeAudit.objects.filter(table__model="piecejointe", objet_id=lien.pk)
        self.assertEqual([e.action for e in entries.order_by("id")], ["creation", "modification"])
        for entry in entries:
            self.assertEqual(entry.module, "agents")
            self.assertEqual(entry.auteur, self.carriere)
            self.assertEqual(entry.objet_libelle, f"CTR — contrat.pdf → {self.cdd}")
