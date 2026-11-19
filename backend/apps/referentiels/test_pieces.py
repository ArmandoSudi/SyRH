"""Document types and the documents each event requires. See specs/2026-11-19-document-types."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import TypeDocument

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
