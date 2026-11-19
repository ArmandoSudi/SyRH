"""Banks. See specs/2026-11-19-banks."""

from datetime import date

from django.db import IntegrityError
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import Banque
from .test_pieces import errors_of, raw

D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
D2025 = date(2025, 7, 1)


def banque(code, nom=None, swift="", *, debut=D2015, fin=None):
    return Banque.objects.create(
        code=code, nom=nom or f"Banque {code}", swift=swift,
        date_ouverture=debut, date_fermeture=fin,
    )  # fmt: skip


class BanqueTests(TestCase):
    def test_bank_is_created_with_its_label(self):
        bcf = banque("bcf ", "Banque Commerciale du Fleuve", " bcflcdki ")

        bcf.refresh_from_db()
        self.assertEqual((bcf.code, bcf.swift), ("BCF", "BCFLCDKI"))
        self.assertEqual(str(bcf), "BCF — Banque Commerciale du Fleuve")

    def test_capitals_through_full_clean(self):
        obj = Banque(code=" bcf", nom="x", swift="bcflcdkixxx", date_ouverture=D2015)
        obj.full_clean()
        self.assertEqual((obj.code, obj.swift), ("BCF", "BCFLCDKIXXX"))

    def test_required_fields_and_optional_swift(self):
        self.assertEqual(set(errors_of(Banque().full_clean)), {"code", "nom", "date_ouverture"})
        Banque(code="X", nom="Sans SWIFT", date_ouverture=D2015).full_clean()

    def test_wrong_swift_is_reported_on_its_field(self):
        for swift in ("ABC", "BCFLCDKIX", "BCFL1DKI", "BCF-CDKI"):
            with self.subTest(swift):
                obj = Banque(code="X", nom="x", swift=swift, date_ouverture=D2015)
                errors = errors_of(obj.full_clean)
                self.assertIn("Code SWIFT/BIC invalide", errors["swift"][0])
                self.assertNotIn("__all__", errors)

    def test_ordered_by_name(self):
        banque("TRC", "Trésor Crédit")
        banque("ACB", "Africa Commerce Bank")
        banque("BCF", "Banque Commerciale du Fleuve")
        self.assertEqual(list(Banque.objects.values_list("code", flat=True)), ["ACB", "BCF", "TRC"])

    def test_same_name_and_same_swift_are_accepted(self):
        banque("B1", "Banque", "BCFLCDKI")
        banque("B2", "Banque", "BCFLCDKI")
        self.assertEqual(Banque.objects.filter(swift="BCFLCDKI").count(), 2)

    def test_no_delete_permission(self):
        self.assertEqual(Banque._meta.default_permissions, ("view", "add", "change"))


class BanqueConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D9)."""

    @classmethod
    def setUpTestData(cls):
        banque("BCF", "Banque Commerciale du Fleuve")

    def assert_refused(self, **values):
        values = {"nom": "x", "date_ouverture": D2015, **values}
        with self.assertRaises(IntegrityError):
            raw(Banque, **values)

    def test_closing_after_opening(self):
        self.assert_refused(code="X1", date_fermeture=D2015)
        self.assert_refused(code="X2", date_fermeture=date(2014, 1, 1))

    def test_code_unique_over_overlapping_periods(self):
        self.assert_refused(code="BCF", date_ouverture=D2020)
        banque("OLD", fin=D2020)
        raw(Banque, code="OLD", nom="x", date_ouverture=D2020)
        self.assert_refused(code="OLD", date_ouverture=date(2019, 12, 31))

    def test_swift_shape(self):
        for i, swift in enumerate(("", "BCFLCDKI", "BCFLCDK1", "BCFLCDKI0A1")):
            raw(Banque, code=f"OK{i}", nom="x", date_ouverture=D2015, swift=swift)
        for i, swift in enumerate(("bcflcdki", "BCFLCDKIX", "BCFL1DKI", "BCFLCD", "BCFLCDKI0A")):
            with self.subTest(swift):
                self.assert_refused(code=f"KO{i}", swift=swift)

    def test_duplicate_code_has_a_french_message_in_forms(self):
        obj = Banque(code="bcf", nom="Bis", date_ouverture=D2020)
        self.assertIn("porte déjà ce code", str(errors_of(obj.full_clean)))

    def test_reversed_dates_report_the_closing_date(self):
        obj = Banque(code="X", nom="X", date_ouverture=D2020, date_fermeture=D2015)
        errors = errors_of(obj.full_clean)
        self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])
        self.assertNotIn("__all__", errors)


class BanqueHistoryTests(TestCase):
    def test_open_from_opening_day_to_closing_day_excluded(self):
        banque("BCF")
        banque("OLD", fin=D2020)
        banque("LATER", debut=D2025)

        def codes_on(day):
            return set(Banque.objects.ouvertes(day).values_list("code", flat=True))

        self.assertEqual(codes_on(date(2014, 12, 31)), set())
        self.assertEqual(codes_on(date(2019, 12, 31)), {"BCF", "OLD"})
        self.assertEqual(codes_on(D2020), {"BCF"})
        self.assertEqual(codes_on(D2025), {"BCF", "LATER"})

    def test_merger_keeps_the_old_name_earlier(self):
        banque("UBK", "Union des Banques du Kasaï", fin=D2020)
        banque("UBK", "Union Bank Kivu-Kasaï", "UBKKCDKI", debut=D2020)

        def name_on(day):
            return Banque.objects.ouvertes(day).get(code="UBK").nom

        self.assertEqual(name_on(date(2019, 12, 31)), "Union des Banques du Kasaï")
        self.assertEqual(name_on(D2020), "Union Bank Kivu-Kasaï")


class BanqueAuditTests(TestCase):
    def test_create_correct_and_close_are_audited(self):
        bcf = banque("BCF", "Banque Comercial du Fleuve")
        bcf.nom = "Banque Commerciale du Fleuve"
        bcf.save()
        bcf.date_fermeture = D2025
        bcf.save()

        entries = EntreeAudit.objects.filter(table__model="banque", objet_id=bcf.pk)
        self.assertEqual(entries.count(), 3)
        self.assertEqual(
            set(entries.values_list("module", "objet_libelle")),
            {
                ("referentiels", "BCF — Banque Comercial du Fleuve"),
                ("referentiels", "BCF — Banque Commerciale du Fleuve"),
            },
        )
