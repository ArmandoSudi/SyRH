"""Classification: catégories (plan group 1). See specs/2026-11-18-classification."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import Categorie

D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
D2025 = date(2025, 7, 1)


def categorie(code, rang, *, debut=D2015, fin=None, nom=None):
    return Categorie.objects.create(
        code=code,
        nom=nom or f"Catégorie {code}",
        rang=rang,
        date_ouverture=debut,
        date_fermeture=fin,
    )


def raw(model, **values):
    """Bypass the model rules, so only the database decides."""
    with transaction.atomic():
        model._base_manager.bulk_create([model(**values)])


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


class CategorieTests(TestCase):
    def test_categorie_is_created_and_audited(self):
        cd = categorie("cd", 4, nom="Cadres de direction")

        cd.refresh_from_db()
        self.assertEqual(cd.code, "CD")
        self.assertEqual(str(cd), "CD — Cadres de direction")
        entry = EntreeAudit.objects.get(objet_id=cd.pk, table__model="categorie")
        self.assertEqual(
            (entry.module, entry.objet_libelle), ("referentiels", "CD — Cadres de direction")
        )

    def test_higher_rank_first(self):
        categorie("EX", 1)
        categorie("CD", 4)
        categorie("AM", 2)

        self.assertEqual(list(Categorie.objects.values_list("code", flat=True)), ["CD", "AM", "EX"])

    def test_no_delete_permission(self):
        self.assertEqual(Categorie._meta.default_permissions, ("view", "add", "change"))


class CategorieConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D12, D15)."""

    @classmethod
    def setUpTestData(cls):
        cls.cd = categorie("CD", 4)

    def assert_refused(self, **values):
        values = {"nom": "x", "rang": 9, "date_ouverture": D2015, **values}
        with self.assertRaises(IntegrityError):
            raw(Categorie, **values)

    def test_rank_is_positive(self):
        self.assert_refused(code="X1", rang=0)

    def test_closing_after_opening(self):
        self.assert_refused(code="X2", date_fermeture=D2015)
        self.assert_refused(code="X3", date_fermeture=date(2014, 1, 1))

    def test_code_unique_over_overlapping_periods(self):
        self.assert_refused(code="CD", date_ouverture=D2020)
        categorie("OLD", 3, fin=D2020)
        # Consecutive periods may share a code: the closing day is the first day closed.
        raw(Categorie, code="OLD", nom="x", rang=2, date_ouverture=D2020)
        self.assert_refused(code="OLD", rang=1, date_ouverture=date(2019, 12, 31))

    def test_rank_unique_over_overlapping_periods(self):
        self.assert_refused(code="X4", rang=4, date_ouverture=D2020)
        categorie("OLD", 3, fin=D2020)
        raw(Categorie, code="NEW", nom="x", rang=3, date_ouverture=D2020)
        self.assert_refused(code="X5", rang=3, date_ouverture=date(2019, 12, 31))

    def test_constraints_have_french_messages_in_forms(self):
        cases = {
            "porte déjà ce code": Categorie(code="cd", nom="Bis", rang=7, date_ouverture=D2020),
            "a déjà ce rang": Categorie(code="NEW", nom="Bis", rang=4, date_ouverture=D2020),
            "supérieur à zéro": Categorie(code="Z", nom="Zéro", rang=0, date_ouverture=D2020),
            "postérieure à la date d'ouverture": Categorie(
                code="F", nom="F", rang=8, date_ouverture=D2020, date_fermeture=D2020
            ),
        }
        for fragment, obj in cases.items():
            with self.subTest(fragment):
                self.assertIn(fragment, str(errors_of(obj.full_clean)))


class CategorieHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categorie("CD", 4)
        categorie("OLD", 3, debut=D2015, fin=D2020)
        categorie("NEW", 3, debut=D2020)
        categorie("LATER", 2, debut=D2025)

    def codes_on(self, day):
        return set(Categorie.objects.ouvertes(day).values_list("code", flat=True))

    def test_open_from_opening_day_to_closing_day_excluded(self):
        self.assertEqual(self.codes_on(date(2014, 12, 31)), set())
        self.assertEqual(self.codes_on(D2015), {"CD", "OLD"})
        self.assertEqual(self.codes_on(date(2019, 12, 31)), {"CD", "OLD"})
        self.assertEqual(self.codes_on(D2020), {"CD", "NEW"})
        self.assertEqual(self.codes_on(date(2025, 6, 30)), {"CD", "NEW"})
        self.assertEqual(self.codes_on(D2025), {"CD", "NEW", "LATER"})

    def test_correct_and_close_are_audited(self):
        cd = Categorie.objects.get(code="CD")
        cd.nom = "Cadres de direction"
        cd.save()
        cd.date_fermeture = D2025
        cd.save()

        entries = EntreeAudit.objects.filter(objet_id=cd.pk, table__model="categorie")
        self.assertEqual(entries.count(), 3)  # created, renamed, closed
        self.assertEqual(entries.latest("pk").objet_libelle, "CD — Cadres de direction")
