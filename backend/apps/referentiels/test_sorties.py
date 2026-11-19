"""Exit reasons and suspension types. See specs/2026-11-19-exit-suspension-reasons."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import MotifSortie, TypeDocument
from .test_pieces import errors_of, raw, type_document

D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
D2025 = date(2025, 7, 1)


def motif(code, nom=None, document=None, *, retraite=False, deces=False, debut=D2015, fin=None):
    return MotifSortie.objects.create(
        code=code, nom=nom or f"Motif {code}",
        type_document=document or TypeDocument.objects.get(code="LDM"),
        retraite=retraite, deces=deces, date_ouverture=debut, date_fermeture=fin,
    )  # fmt: skip


class MotifSortieTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ldm = type_document("LDM", "Lettre de démission")
        cls.adc = type_document("ADC", "Acte de décès")

    def test_reason_is_created_with_its_label(self):
        dem = motif("dem ", "Démission")

        dem.refresh_from_db()
        self.assertEqual(dem.code, "DEM")
        self.assertEqual(str(dem), "DEM — Démission")
        self.assertFalse(dem.retraite or dem.deces)

    def test_code_in_capitals_through_full_clean(self):
        obj = MotifSortie(code=" dcd", nom="Décès", type_document=self.adc, date_ouverture=D2015)
        obj.full_clean()
        self.assertEqual(obj.code, "DCD")

    def test_required_fields(self):
        self.assertEqual(
            set(errors_of(MotifSortie().full_clean)),
            {"code", "nom", "type_document", "date_ouverture"},
        )

    def test_ordered_by_name(self):
        motif("RET", "Retraite pour ancienneté")
        motif("DCD", "Décès")
        motif("DEM", "Démission")
        self.assertEqual(
            list(MotifSortie.objects.values_list("code", flat=True)), ["DCD", "DEM", "RET"]
        )

    def test_same_name_and_same_document_are_accepted(self):
        motif("R1", "Retraite")
        motif("R2", "Retraite")
        self.assertEqual(self.ldm.motifs_sortie.count(), 2)

    def test_retirement_and_death_together_reported_on_death(self):
        obj = MotifSortie(code="X", nom="X", type_document=self.adc, date_ouverture=D2015,
                          retraite=True, deces=True)  # fmt: skip
        self.assertIn("à la fois une retraite et un décès", errors_of(obj.full_clean)["deces"][0])

    def test_no_delete_permission(self):
        self.assertEqual(MotifSortie._meta.default_permissions, ("view", "add", "change"))

    def test_deleting_a_document_type_in_use_is_refused(self):
        motif("DEM")
        with self.assertRaises(ProtectedError):
            self.ldm.delete()


class MotifSortieConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D11)."""

    @classmethod
    def setUpTestData(cls):
        cls.ldm = type_document("LDM", "Lettre de démission")
        motif("DEM", "Démission")

    def assert_refused(self, **values):
        values = {"nom": "x", "type_document": self.ldm, "date_ouverture": D2015, **values}
        with self.assertRaises(IntegrityError):
            raw(MotifSortie, **values)

    def test_closing_after_opening(self):
        self.assert_refused(code="X1", date_fermeture=D2015)
        self.assert_refused(code="X2", date_fermeture=date(2014, 1, 1))

    def test_code_unique_over_overlapping_periods(self):
        self.assert_refused(code="DEM", date_ouverture=D2020)
        motif("OLD", fin=D2020)
        raw(MotifSortie, code="OLD", nom="x", type_document=self.ldm, date_ouverture=D2020)
        self.assert_refused(code="OLD", date_ouverture=date(2019, 12, 31))

    def test_not_both_retirement_and_death(self):
        self.assert_refused(code="X", retraite=True, deces=True)
        raw(MotifSortie, code="R", nom="x", type_document=self.ldm, date_ouverture=D2015,
            retraite=True)  # fmt: skip

    def test_duplicate_code_has_a_french_message_in_forms(self):
        obj = MotifSortie(code="dem", nom="Bis", type_document=self.ldm, date_ouverture=D2020)
        self.assertIn("porte déjà ce code", str(errors_of(obj.full_clean)))

    def test_reversed_dates_report_the_closing_date(self):
        obj = MotifSortie(code="X", nom="X", type_document=self.ldm, date_ouverture=D2020,
                          date_fermeture=D2015)  # fmt: skip
        errors = errors_of(obj.full_clean)
        self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])
        self.assertNotIn("__all__", errors)


class MotifSortieRuleTests(TestCase):
    """The reason stays within its document type's period (D9), from full_clean() and save()."""

    @classmethod
    def setUpTestData(cls):
        cls.ldm = type_document("LDM", "Lettre de démission", debut=D2020)

    def test_reason_within_its_document_period(self):
        early = MotifSortie(code="DEM", nom="Démission", type_document=self.ldm,
                            date_ouverture=D2015)  # fmt: skip
        self.assertIn("ne peut pas ouvrir avant son type de pièce",
                      errors_of(early.full_clean)["date_ouverture"][0])  # fmt: skip
        with self.assertRaises(ValidationError):
            early.save()

        closed = type_document("OLD", debut=D2015, fin=D2020)
        late = MotifSortie(code="DEM", nom="Démission", type_document=closed,
                           date_ouverture=D2015)  # fmt: skip
        self.assertIn("fermeture de son type de pièce",
                      errors_of(late.full_clean)["date_fermeture"][0])  # fmt: skip
        with self.assertRaises(ValidationError):
            late.save()
        late.date_fermeture = D2020
        late.full_clean()

    def test_document_cannot_close_while_a_reason_stays_open(self):
        motif("DEM", debut=D2020)
        self.ldm.date_fermeture = D2025
        errors = errors_of(self.ldm.full_clean)
        self.assertIn("Des motifs de sortie restent ouverts après cette date : DEM",
                      errors["date_fermeture"][0])  # fmt: skip
        with self.assertRaises(ValidationError):
            self.ldm.save()

    def test_document_cannot_open_after_a_reason(self):
        motif("DEM", debut=D2020)
        self.ldm.date_ouverture = D2025
        self.assertIn("Des motifs de sortie ouvrent avant cette date",
                      errors_of(self.ldm.full_clean)["date_ouverture"][0])  # fmt: skip

    def test_document_can_close_once_its_reasons_are_closed(self):
        motif("DEM", debut=D2020, fin=D2025)
        self.ldm.date_fermeture = D2025
        self.ldm.full_clean()
        self.ldm.save()

    def test_document_and_flags_can_be_corrected(self):
        dem = motif("DEM", debut=D2020)
        other = type_document("LTR", "Lettre", debut=D2015)
        dem.type_document = other
        dem.retraite = True
        dem.full_clean()
        dem.save()
        dem.refresh_from_db()
        self.assertEqual(dem.type_document, other)

    def test_changing_the_document_keeps_the_old_one_earlier(self):
        new = type_document("LTR", "Lettre de démission manuscrite", debut=D2015)
        motif("DEM", debut=D2020, fin=D2025)
        motif("DEM", document=new, debut=D2025)

        def document_on(day):
            return MotifSortie.objects.ouvertes(day).get(code="DEM").type_document.code

        self.assertEqual(document_on(D2020), "LDM")
        self.assertEqual(document_on(D2025), "LTR")


class MotifSortieHistoryTests(TestCase):
    def test_open_from_opening_day_to_closing_day_excluded(self):
        type_document("LDM")
        motif("DEM")
        motif("OLD", fin=D2020)
        motif("LATER", debut=D2025)

        def codes_on(day):
            return set(MotifSortie.objects.ouvertes(day).values_list("code", flat=True))

        self.assertEqual(codes_on(date(2014, 12, 31)), set())
        self.assertEqual(codes_on(date(2019, 12, 31)), {"DEM", "OLD"})
        self.assertEqual(codes_on(D2020), {"DEM"})
        self.assertEqual(codes_on(D2025), {"DEM", "LATER"})


class MotifSortieAuditTests(TestCase):
    def test_create_correct_and_close_are_audited(self):
        type_document("LDM")
        dem = motif("DEM", "Démision")
        dem.nom = "Démission"
        dem.save()
        dem.date_fermeture = D2025
        dem.save()

        entries = EntreeAudit.objects.filter(table__model="motifsortie", objet_id=dem.pk)
        self.assertEqual(entries.count(), 3)
        self.assertEqual(
            set(entries.values_list("module", "objet_libelle")),
            {("referentiels", "DEM — Démision"), ("referentiels", "DEM — Démission")},
        )
