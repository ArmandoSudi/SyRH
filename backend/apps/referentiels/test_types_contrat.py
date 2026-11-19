"""Contract types. See specs/2026-11-19-contract-types."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import TypeContrat

D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
D2025 = date(2025, 7, 1)


def type_contrat(code, nom=None, *, fixe=False, essai=True, debut=D2015, fin=None):
    return TypeContrat.objects.create(
        code=code,
        nom=nom or f"Type {code}",
        duree_determinee=fixe,
        periode_essai=essai,
        date_ouverture=debut,
        date_fermeture=fin,
    )


def raw(**values):
    """Bypass the model, so only the database decides."""
    values = {
        "nom": "x",
        "duree_determinee": False,
        "periode_essai": False,
        "date_ouverture": D2015,
        **values,
    }
    with transaction.atomic():
        TypeContrat._base_manager.bulk_create([TypeContrat(**values)])


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


class TypeContratTests(TestCase):
    def test_type_is_created_with_its_label_and_flags(self):
        cdd = type_contrat("cdd ", "Contrat à durée déterminée", fixe=True, essai=True)

        cdd.refresh_from_db()
        self.assertEqual(cdd.code, "CDD")
        self.assertEqual(str(cdd), "CDD — Contrat à durée déterminée")
        self.assertEqual((cdd.duree_determinee, cdd.periode_essai), (True, True))

    def test_code_in_capitals_through_full_clean(self):
        obj = TypeContrat(
            code=" stg", nom="Stage", duree_determinee=True, periode_essai=False,
            date_ouverture=D2015,
        )  # fmt: skip
        obj.full_clean()
        self.assertEqual(obj.code, "STG")

    def test_required_fields(self):
        obj = TypeContrat(duree_determinee=None, periode_essai=None)
        self.assertEqual(
            set(errors_of(obj.full_clean)),
            {"code", "nom", "duree_determinee", "periode_essai", "date_ouverture"},
        )

    def test_ordered_by_name(self):
        type_contrat("STG", "Stage")
        type_contrat("CDI", "Contrat à durée indéterminée")
        type_contrat("JRN", "Journalier")

        self.assertEqual(
            list(TypeContrat.objects.values_list("code", flat=True)), ["CDI", "JRN", "STG"]
        )

    def test_same_name_is_accepted(self):
        type_contrat("A1", "Apprentissage")
        type_contrat("A2", "Apprentissage")
        self.assertEqual(TypeContrat.objects.filter(nom="Apprentissage").count(), 2)

    def test_no_delete_permission(self):
        self.assertEqual(TypeContrat._meta.default_permissions, ("view", "add", "change"))


class TypeContratConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D9)."""

    @classmethod
    def setUpTestData(cls):
        type_contrat("CDI", "Contrat à durée indéterminée")

    def assert_refused(self, **values):
        with self.assertRaises(IntegrityError):
            raw(**values)

    def test_closing_after_opening(self):
        self.assert_refused(code="X1", date_fermeture=D2015)
        self.assert_refused(code="X2", date_fermeture=date(2014, 1, 1))

    def test_code_unique_over_overlapping_periods(self):
        self.assert_refused(code="CDI", date_ouverture=D2020)
        type_contrat("OLD", fin=D2020)
        # Consecutive periods may share a code: the closing day is the first day closed.
        raw(code="OLD", date_ouverture=D2020)
        self.assert_refused(code="OLD", date_ouverture=date(2019, 12, 31))

    def test_duplicate_code_has_a_french_message_in_forms(self):
        obj = TypeContrat(
            code="cdi", nom="Bis", duree_determinee=False, periode_essai=True,
            date_ouverture=D2020,
        )  # fmt: skip
        self.assertIn("porte déjà ce code", str(errors_of(obj.full_clean)))

    def test_reversed_dates_report_the_closing_date(self):
        obj = TypeContrat(
            code="X", nom="X", duree_determinee=False, periode_essai=False,
            date_ouverture=D2020, date_fermeture=D2015,
        )  # fmt: skip
        errors = errors_of(obj.full_clean)
        self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])
        self.assertNotIn("__all__", errors)


class TypeContratHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        type_contrat("CDI", "Contrat à durée indéterminée")
        type_contrat("APP", "Contrat d'apprentissage", fixe=True, fin=D2020)  # retired
        type_contrat("LATER", debut=D2025)

    def codes_on(self, day):
        return set(TypeContrat.objects.ouvertes(day).values_list("code", flat=True))

    def test_open_from_opening_day_to_closing_day_excluded(self):
        self.assertEqual(self.codes_on(date(2014, 12, 31)), set())
        self.assertEqual(self.codes_on(D2015), {"CDI", "APP"})
        self.assertEqual(self.codes_on(date(2019, 12, 31)), {"CDI", "APP"})
        self.assertEqual(self.codes_on(D2020), {"CDI"})  # retired, no successor
        self.assertEqual(self.codes_on(D2025), {"CDI", "LATER"})

    def test_changing_a_flag_keeps_the_old_rule_at_earlier_dates(self):
        cdi = TypeContrat.objects.get(code="CDI")
        cdi.date_fermeture = D2025
        cdi.save()
        type_contrat("CDI", "Contrat à durée indéterminée", essai=False, debut=D2025)

        def essai_on(day):
            return TypeContrat.objects.ouvertes(day).get(code="CDI").periode_essai

        self.assertTrue(essai_on(date(2025, 6, 30)))
        self.assertFalse(essai_on(D2025))


class TypeContratAuditTests(TestCase):
    def test_create_correct_and_close_are_audited(self):
        cdd = type_contrat("CDD", "Contrat a duree determinee", fixe=True)
        cdd.nom = "Contrat à durée déterminée"
        cdd.save()
        cdd.date_fermeture = D2025
        cdd.save()

        entries = EntreeAudit.objects.filter(table__model="typecontrat", objet_id=cdd.pk)
        self.assertEqual(entries.count(), 3)
        self.assertEqual(
            set(entries.values_list("module", "objet_libelle")),
            {
                ("referentiels", "CDD — Contrat a duree determinee"),
                ("referentiels", "CDD — Contrat à durée déterminée"),
            },
        )
