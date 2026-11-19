"""Document types and the documents each event requires. See specs/2026-11-19-document-types."""

import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import PieceRequise, TypeDocument

E = PieceRequise.Evenement

D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
D2025 = date(2025, 7, 1)


def type_document(code, nom=None, *, debut=D2015, fin=None):
    return TypeDocument.objects.create(
        code=code, nom=nom or f"Pièce {code}", date_ouverture=debut, date_fermeture=fin
    )


def raw(model, **values):
    """Bypass the model, so only the database decides."""
    with transaction.atomic():
        model._base_manager.bulk_create([model(**values)])


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


class TypeDocumentTests(TestCase):
    def test_type_is_created_with_its_label(self):
        ana = type_document("ana ", "Acte de naissance")

        ana.refresh_from_db()
        self.assertEqual(ana.code, "ANA")
        self.assertEqual(str(ana), "ANA — Acte de naissance")

    def test_code_in_capitals_through_full_clean(self):
        obj = TypeDocument(code=" ama", nom="Acte de mariage", date_ouverture=D2015)
        obj.full_clean()
        self.assertEqual(obj.code, "AMA")

    def test_required_fields(self):
        self.assertEqual(
            set(errors_of(TypeDocument().full_clean)), {"code", "nom", "date_ouverture"}
        )

    def test_ordered_by_name(self):
        type_document("DIP", "Diplôme")
        type_document("ANA", "Acte de naissance")
        type_document("CTR", "Contrat signé")
        self.assertEqual(
            list(TypeDocument.objects.values_list("code", flat=True)), ["ANA", "CTR", "DIP"]
        )

    def test_same_name_is_accepted(self):
        type_document("D1", "Décision")
        type_document("D2", "Décision")
        self.assertEqual(TypeDocument.objects.filter(nom="Décision").count(), 2)

    def test_no_delete_permission(self):
        self.assertEqual(TypeDocument._meta.default_permissions, ("view", "add", "change"))


class TypeDocumentConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D11)."""

    @classmethod
    def setUpTestData(cls):
        type_document("ANA", "Acte de naissance")

    def assert_refused(self, **values):
        values = {"nom": "x", "date_ouverture": D2015, **values}
        with self.assertRaises(IntegrityError):
            raw(TypeDocument, **values)

    def test_closing_after_opening(self):
        self.assert_refused(code="X1", date_fermeture=D2015)
        self.assert_refused(code="X2", date_fermeture=date(2014, 1, 1))

    def test_code_unique_over_overlapping_periods(self):
        self.assert_refused(code="ANA", date_ouverture=D2020)
        type_document("OLD", fin=D2020)
        raw(TypeDocument, code="OLD", nom="x", date_ouverture=D2020)
        self.assert_refused(code="OLD", date_ouverture=date(2019, 12, 31))

    def test_duplicate_code_has_a_french_message_in_forms(self):
        obj = TypeDocument(code="ana", nom="Bis", date_ouverture=D2020)
        self.assertIn("porte déjà ce code", str(errors_of(obj.full_clean)))

    def test_reversed_dates_report_the_closing_date(self):
        obj = TypeDocument(code="X", nom="X", date_ouverture=D2020, date_fermeture=D2015)
        errors = errors_of(obj.full_clean)
        self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])
        self.assertNotIn("__all__", errors)


class TypeDocumentHistoryTests(TestCase):
    def test_open_from_opening_day_to_closing_day_excluded(self):
        type_document("ANA")
        type_document("CJ", "Extrait de casier judiciaire", fin=D2020)
        type_document("LATER", debut=D2025)

        def codes_on(day):
            return set(TypeDocument.objects.ouvertes(day).values_list("code", flat=True))

        self.assertEqual(codes_on(date(2014, 12, 31)), set())
        self.assertEqual(codes_on(date(2019, 12, 31)), {"ANA", "CJ"})
        self.assertEqual(codes_on(D2020), {"ANA"})
        self.assertEqual(codes_on(D2025), {"ANA", "LATER"})


class TypeDocumentAuditTests(TestCase):
    def test_create_correct_and_close_are_audited(self):
        ana = type_document("ANA", "Acte de naisance")
        ana.nom = "Acte de naissance"
        ana.save()
        ana.date_fermeture = D2025
        ana.save()

        entries = EntreeAudit.objects.filter(table__model="typedocument", objet_id=ana.pk)
        self.assertEqual(entries.count(), 3)
        self.assertEqual(
            set(entries.values_list("module", "objet_libelle")),
            {
                ("referentiels", "ANA — Acte de naisance"),
                ("referentiels", "ANA — Acte de naissance"),
            },
        )


def piece(evenement, type_doc, obligatoire=True, *, debut=D2015, fin=None):
    return PieceRequise.objects.create(
        evenement=evenement, type_document=type_doc, obligatoire=obligatoire,
        date_ouverture=debut, date_fermeture=fin,
    )  # fmt: skip


class PieceRequiseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ctr = type_document("CTR", "Contrat signé")
        cls.dec = type_document("DEC", "Décision")
        cls.cni = type_document("CNI", "Pièce d'identité")

    def test_requirement_is_created_with_its_label(self):
        req = piece(E.ENGAGEMENT, self.ctr)
        self.assertEqual(str(req), "Engagement — CTR (obligatoire)")
        self.assertEqual(str(piece(E.FORMATION, self.dec, False)), "Formation — DEC (facultative)")

    def test_required_fields(self):
        obj = PieceRequise(obligatoire=None)
        self.assertEqual(
            set(errors_of(obj.full_clean)),
            {"evenement", "type_document", "obligatoire", "date_ouverture"},
        )

    def test_one_document_serves_several_events(self):
        for evenement in (E.PROMOTION, E.MUTATION, E.INTERIM):
            piece(evenement, self.dec)
        self.assertEqual(self.dec.pieces_requises.count(), 3)

    def test_event_order_then_mandatory_first_then_name(self):
        piece(E.FORMATION, self.dec, False)
        piece(E.ENGAGEMENT, self.dec, False)
        piece(E.ENGAGEMENT, self.cni)
        piece(E.ENGAGEMENT, self.ctr)
        piece(E.PROMOTION, self.dec)

        self.assertEqual(
            [str(p) for p in PieceRequise.objects.all()],
            [
                "Engagement — CTR (obligatoire)",
                "Engagement — CNI (obligatoire)",
                "Engagement — DEC (facultative)",
                "Promotion — DEC (obligatoire)",
                "Formation — DEC (facultative)",
            ],
        )

    def test_no_delete_permission(self):
        self.assertEqual(PieceRequise._meta.default_permissions, ("view", "add", "change"))

    def test_deleting_a_required_type_is_refused(self):
        piece(E.ENGAGEMENT, self.ctr)
        with self.assertRaises(ProtectedError):
            self.ctr.delete()


class PieceRequiseConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D11)."""

    @classmethod
    def setUpTestData(cls):
        cls.dec = type_document("DEC", "Décision")
        piece(E.PROMOTION, cls.dec)

    def assert_refused(self, **values):
        values = {"type_document": self.dec, "obligatoire": True, "date_ouverture": D2015,
                  **values}  # fmt: skip
        with self.assertRaises(IntegrityError):
            raw(PieceRequise, **values)

    def test_event_is_one_of_the_list(self):
        self.assert_refused(evenement="absence")

    def test_closing_after_opening(self):
        self.assert_refused(evenement=E.MUTATION, date_fermeture=D2015)

    def test_same_document_twice_for_one_event_over_overlapping_periods(self):
        self.assert_refused(evenement=E.PROMOTION, date_ouverture=D2020)
        raw(PieceRequise, evenement=E.MUTATION, type_document=self.dec, obligatoire=True,
            date_ouverture=D2015)  # another event: accepted  # fmt: skip

    def test_same_document_on_consecutive_periods(self):
        piece(E.INTERIM, self.dec, fin=D2020)
        raw(PieceRequise, evenement=E.INTERIM, type_document=self.dec, obligatoire=False,
            date_ouverture=D2020)  # fmt: skip
        self.assertEqual(PieceRequise.objects.filter(evenement=E.INTERIM).count(), 2)

    def test_duplicate_has_a_french_message_in_forms(self):
        obj = PieceRequise(evenement=E.PROMOTION, type_document=self.dec, obligatoire=False,
                           date_ouverture=D2020)  # fmt: skip
        self.assertIn("exige déjà ce type de pièce", str(errors_of(obj.full_clean)))

    def test_reversed_dates_report_the_closing_date(self):
        obj = PieceRequise(evenement=E.MUTATION, type_document=self.dec, obligatoire=True,
                           date_ouverture=D2020, date_fermeture=D2015)  # fmt: skip
        errors = errors_of(obj.full_clean)
        self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])


class PieceRequiseRuleTests(TestCase):
    """Rules that read other rows (D8, D9), from full_clean() and save()."""

    @classmethod
    def setUpTestData(cls):
        cls.ana = type_document("ANA", "Acte de naissance", debut=D2020)
        cls.other = type_document("AMA", "Acte de mariage")

    def test_requirement_within_its_type_period(self):
        early = PieceRequise(evenement=E.NAISSANCE, type_document=self.ana, obligatoire=True,
                             date_ouverture=D2015)  # fmt: skip
        self.assertIn("ne peut pas ouvrir avant son type de pièce",
                      errors_of(early.full_clean)["date_ouverture"][0])  # fmt: skip
        with self.assertRaises(ValidationError):
            early.save()

        closed = type_document("OLD", debut=D2015, fin=D2020)
        late = PieceRequise(evenement=E.NAISSANCE, type_document=closed, obligatoire=True,
                            date_ouverture=D2015)  # fmt: skip
        self.assertIn("fermeture de son type de pièce",
                      errors_of(late.full_clean)["date_fermeture"][0])  # fmt: skip

    def test_type_cannot_close_while_a_requirement_stays_open(self):
        piece(E.NAISSANCE, self.ana, debut=D2020)
        self.ana.date_fermeture = D2025
        errors = errors_of(self.ana.full_clean)
        self.assertIn("Des pièces exigées restent ouvertes", errors["date_fermeture"][0])

    def test_event_and_type_never_change_but_flag_and_dates_can(self):
        req = piece(E.NAISSANCE, self.ana, debut=D2020)
        for field, value in (("evenement", E.MARIAGE), ("type_document", self.other)):
            with self.subTest(field):
                obj = PieceRequise.objects.get(pk=req.pk)
                setattr(obj, field, value)
                self.assertIn("Ne peut pas être modifié", errors_of(obj.full_clean)[field][0])
                with self.assertRaises(ValidationError):
                    obj.save()

        req.obligatoire = False
        req.date_ouverture = D2025
        req.save()
        req.refresh_from_db()
        self.assertEqual((req.obligatoire, req.date_ouverture), (False, D2025))

    def test_making_a_document_optional_keeps_the_old_rule_earlier(self):
        req = piece(E.NAISSANCE, self.ana, debut=D2020)
        req.date_fermeture = D2025
        req.save()
        piece(E.NAISSANCE, self.ana, False, debut=D2025)

        def obligatoire_on(day):
            return PieceRequise.objects.ouvertes(day).get(evenement=E.NAISSANCE).obligatoire

        self.assertTrue(obligatoire_on(date(2025, 6, 30)))
        self.assertFalse(obligatoire_on(D2025))


class PieceRequiseAuditTests(TestCase):
    def test_create_correct_and_close_are_audited(self):
        dec = type_document("DEC", "Décision")
        req = piece(E.PROMOTION, dec, False)
        req.obligatoire = True
        req.save()
        req.date_fermeture = D2025
        req.save()

        entries = EntreeAudit.objects.filter(table__model="piecerequise", objet_id=req.pk)
        self.assertEqual(entries.count(), 3)
        self.assertEqual(
            set(entries.values_list("module", "objet_libelle")),
            {("referentiels", "Promotion — DEC (facultative)"),
             ("referentiels", "Promotion — DEC (obligatoire)")},
        )  # fmt: skip


class EvenementMirrorTests(TestCase):
    """The screen lists event kinds from its own copy of the list (document types D21)."""

    def test_frontend_list_matches_the_backend(self):
        source = (
            Path(settings.BASE_DIR).parent
            / "frontend/src/features/referentiels/components/pieces.ts"
        ).read_text()
        pairs = re.findall(r"\{ value: '([a-z_]+)', label: '([^']+)' \}", source)
        self.assertEqual(pairs, [(value, str(label)) for value, label in E.choices])
