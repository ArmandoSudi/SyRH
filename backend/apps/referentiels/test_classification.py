"""Classification: catégories, grades, échelons. See specs/2026-11-18-classification."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import Categorie, Echelon, Grade

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


def grade(code, cat, rang, *, debut=D2015, fin=None, nom=None):
    return Grade.objects.create(
        code=code,
        nom=nom or f"Grade {code}",
        categorie=cat,
        rang=rang,
        date_ouverture=debut,
        date_fermeture=fin,
    )


def echelon(gr, numero, *, debut=D2015, fin=None):
    return Echelon.objects.create(grade=gr, numero=numero, date_ouverture=debut, date_fermeture=fin)


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


class GradeEchelonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cd = categorie("CD", 4)
        cls.am = categorie("AM", 2)

    def test_grade_and_echelon_are_created_and_audited(self):
        a1 = grade("a1", self.cd, 1, nom="Attaché de 1re classe")
        step = echelon(a1, 3)

        self.assertEqual(a1.code, "A1")
        self.assertEqual(str(a1), "A1 — Attaché de 1re classe")
        self.assertEqual(str(step), "A1 — Échelon 3")
        self.assertEqual(step.libelle, "A1 — Échelon 3")
        for model, obj in (("grade", a1), ("echelon", step)):
            with self.subTest(model):
                entry = EntreeAudit.objects.get(objet_id=obj.pk, table__model=model)
                self.assertEqual((entry.module, entry.objet_libelle), ("referentiels", str(obj)))

    def test_order_follows_categorie_then_grade_then_number(self):
        low = grade("M1", self.am, 9)  # high rank, but in a lower catégorie
        mid = grade("A2", self.cd, 1)
        top = grade("A1", self.cd, 2)

        self.assertGreater(top.cle_ordre, mid.cle_ordre)
        self.assertGreater(mid.cle_ordre, low.cle_ordre)
        self.assertEqual(list(Grade.objects.all()), [top, mid, low])

        for numero in (3, 1, 2):
            echelon(mid, numero)
        echelon(top, 1)
        self.assertEqual(
            [str(e) for e in Echelon.objects.all()],
            ["A1 — Échelon 1", "A2 — Échelon 1", "A2 — Échelon 2", "A2 — Échelon 3"],
        )

    def test_gaps_in_echelon_numbers_are_accepted(self):
        a1 = grade("A1", self.cd, 1)
        for numero in (1, 2, 4):
            echelon(a1, numero)
        self.assertEqual(list(a1.echelons.values_list("numero", flat=True)), [1, 2, 4])

    def test_no_delete_permission(self):
        for model in (Grade, Echelon):
            with self.subTest(model.__name__):
                self.assertEqual(model._meta.default_permissions, ("view", "add", "change"))

    def test_referenced_rows_are_protected(self):
        a1 = grade("A1", self.cd, 1)
        echelon(a1, 1)
        for obj in (self.cd, a1):
            with self.subTest(type(obj).__name__), self.assertRaises(ProtectedError):
                type(obj)._base_manager.filter(pk=obj.pk).delete()


class GradeEchelonConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL without the model (D12, D15)."""

    @classmethod
    def setUpTestData(cls):
        cls.cd = categorie("CD", 4)
        cls.am = categorie("AM", 2)
        cls.a1 = grade("A1", cls.cd, 1)
        echelon(cls.a1, 1)

    def assert_refused(self, model, **values):
        with self.assertRaises(IntegrityError):
            raw(model, **{"date_ouverture": D2015, **values})

    def grade_values(self, **values):
        return {"nom": "x", "categorie": self.cd, "rang": 9, "date_ouverture": D2015, **values}

    def test_grade_rank_is_positive(self):
        self.assert_refused(Grade, **self.grade_values(code="X1", rang=0))

    def test_echelon_number_is_positive(self):
        self.assert_refused(Echelon, grade=self.a1, numero=0)

    def test_closing_after_opening(self):
        self.assert_refused(Grade, **self.grade_values(code="X2", date_fermeture=D2015))
        self.assert_refused(Echelon, grade=self.a1, numero=5, date_fermeture=date(2014, 1, 1))

    def test_grade_code_unique_across_the_grid(self):
        self.assert_refused(Grade, **self.grade_values(code="A1", date_ouverture=D2020))
        # Even in another catégorie (D3).
        self.assert_refused(Grade, **self.grade_values(code="A1", categorie=self.am))
        grade("OLD", self.am, 1, fin=D2020)
        raw(Grade, **self.grade_values(code="OLD", categorie=self.am, date_ouverture=D2020))

    def test_grade_rank_unique_within_its_categorie(self):
        self.assert_refused(Grade, **self.grade_values(code="X3", rang=1, date_ouverture=D2020))
        # Another catégorie may use the same rank.
        raw(Grade, **self.grade_values(code="M1", categorie=self.am, rang=1))
        grade("OLD", self.cd, 2, fin=D2020)
        raw(Grade, **self.grade_values(code="NEW", rang=2, date_ouverture=D2020))

    def test_echelon_number_unique_within_its_grade(self):
        self.assert_refused(Echelon, grade=self.a1, numero=1, date_ouverture=D2020)
        other = grade("A2", self.cd, 2)
        raw(
            Echelon, grade=other, numero=1, date_ouverture=D2015
        )  # another grade may use the same number
        echelon(self.a1, 2, fin=D2020)
        raw(Echelon, grade=self.a1, numero=2, date_ouverture=D2020)

    def test_constraints_have_french_messages_in_forms(self):
        cases = {
            "Un autre grade porte déjà ce code": Grade(
                code="a1", nom="Bis", categorie=self.am, rang=5, date_ouverture=D2020
            ),
            "Un autre grade de cette catégorie a déjà ce rang": Grade(
                code="A9", nom="Bis", categorie=self.cd, rang=1, date_ouverture=D2020
            ),
            "Ce grade a déjà un échelon de ce numéro": Echelon(
                grade=self.a1, numero=1, date_ouverture=D2020
            ),
            "Le numéro doit être supérieur à zéro": Echelon(
                grade=self.a1, numero=0, date_ouverture=D2020
            ),
        }
        for fragment, obj in cases.items():
            with self.subTest(fragment):
                self.assertIn(fragment, str(errors_of(obj.full_clean)))


class ClassificationRuleTests(TestCase):
    """Rules that read other rows, checked by clean() and by save() (D11, D13, D16)."""

    @classmethod
    def setUpTestData(cls):
        cls.cd = categorie("CD", 4)
        cls.am = categorie("AM", 2)
        cls.a1 = grade("A1", cls.cd, 1)
        cls.e1 = echelon(cls.a1, 1)

    def check_both(self, obj, field, fragment):
        """The same error from full_clean() (forms) and from save() (scripts)."""
        for call in (obj.full_clean, obj.save):
            with self.subTest(call.__name__):
                messages = errors_of(call)
                self.assertIn(field, messages)
                self.assertIn(fragment, " ".join(messages[field]))

    def fresh(self, obj):
        return type(obj).objects.get(pk=obj.pk)

    def test_parent_never_changes(self):
        a1 = self.fresh(self.a1)
        a1.categorie = self.am
        self.check_both(a1, "categorie", "fermez le grade et ouvrez-en un nouveau")

        e1 = self.fresh(self.e1)
        e1.grade = grade("A2", self.cd, 2)
        self.check_both(e1, "grade", "fermez l'échelon et ouvrez-en un nouveau")

    def test_codes_names_ranks_numbers_and_dates_can_be_corrected(self):
        a1 = self.fresh(self.a1)
        a1.code, a1.nom, a1.rang, a1.date_ouverture = "a1b", "Corrigé", 3, D2015
        a1.full_clean()
        a1.save()
        self.assertEqual(self.fresh(a1).code, "A1B")

        e1 = self.fresh(self.e1)
        e1.numero, e1.date_ouverture = 2, D2020
        e1.full_clean()
        e1.save()

    def test_cannot_open_before_its_parent(self):
        late = categorie("LATE", 1, debut=D2020)
        self.check_both(
            Grade(code="L1", nom="x", categorie=late, rang=1, date_ouverture=D2015),
            "date_ouverture",
            "Le grade ne peut pas ouvrir avant sa catégorie (01/01/2020).",
        )
        late_grade = grade("L2", late, 2, debut=D2020)
        self.check_both(
            Echelon(grade=late_grade, numero=1, date_ouverture=D2015),
            "date_ouverture",
            "L'échelon ne peut pas ouvrir avant son grade (01/01/2020).",
        )

    def test_cannot_stay_open_after_its_parent(self):
        short = categorie("SHORT", 1, fin=D2025)
        message = "au plus tard à la fermeture de sa catégorie (01/07/2025)"
        self.check_both(
            Grade(code="S1", nom="x", categorie=short, rang=1, date_ouverture=D2015),
            "date_fermeture",
            message,
        )
        short_grade = grade("S2", short, 2, fin=D2025)
        self.check_both(
            Echelon(
                grade=short_grade, numero=1, date_ouverture=D2015, date_fermeture=date(2026, 1, 1)
            ),
            "date_fermeture",
            "au plus tard à la fermeture de son grade (01/07/2025)",
        )
        echelon(short_grade, 1, debut=D2020, fin=D2025)

    def test_parent_cannot_close_before_its_children(self):
        cd = self.fresh(self.cd)
        cd.date_fermeture = D2025
        self.check_both(
            cd, "date_fermeture", "Des grades rattachés restent ouverts après cette date : A1."
        )

        a1 = self.fresh(self.a1)
        a1.date_fermeture = D2025
        self.check_both(
            a1,
            "date_fermeture",
            "Des échelons rattachés restent ouverts après cette date : échelon 1.",
        )

        e1 = self.fresh(self.e1)
        e1.date_fermeture = D2025
        e1.save()
        a1.save()
        cd.save()

    def test_parent_cannot_open_after_its_children(self):
        cd = self.fresh(self.cd)
        cd.date_ouverture = D2020
        self.check_both(cd, "date_ouverture", "Des grades rattachés ouvrent avant cette date : A1.")

        a1 = self.fresh(self.a1)
        a1.date_ouverture = D2020
        self.check_both(a1, "date_ouverture", "échelon 1")

    def test_an_echelon_opens_and_closes_on_its_own(self):
        echelon(self.a1, 2, debut=D2020)
        e1 = self.fresh(self.e1)
        e1.date_fermeture = D2025
        e1.save()
        self.assertEqual(
            list(Echelon.objects.ouvertes(D2025).values_list("numero", flat=True)), [2]
        )
        self.assertIsNone(self.fresh(self.a1).date_fermeture)


class ClassificationHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cd = categorie("CD", 4)
        cls.old = grade("A1", cls.cd, 1, nom="Attaché (ancien)")
        cls.old_steps = [echelon(cls.old, n) for n in (1, 2)]

    def numbers_on(self, day):
        return set(Echelon.objects.ouvertes(day).values_list("numero", flat=True))

    def test_open_from_opening_day_to_closing_day_excluded(self):
        echelon(self.old, 3, debut=D2020, fin=D2025)
        numbers = self.numbers_on

        self.assertEqual(numbers(date(2019, 12, 31)), {1, 2})
        self.assertEqual(numbers(D2020), {1, 2, 3})
        self.assertEqual(numbers(date(2025, 6, 30)), {1, 2, 3})
        self.assertEqual(numbers(D2025), {1, 2})
        self.assertEqual(Grade.objects.ouvertes(date(2014, 12, 31)).count(), 0)

    def test_reform_keeps_the_old_grid(self):
        for step in self.old_steps:
            step.date_fermeture = D2020
            step.save()
        old = Grade.objects.get(pk=self.old.pk)
        old.date_fermeture = D2020
        old.save()

        new = grade("A1", self.cd, 1, debut=D2020, nom="Attaché (réformé)")
        for n in (1, 2, 3):
            echelon(new, n, debut=D2020)

        with self.assertRaises(IntegrityError), transaction.atomic():
            raw(
                Grade,
                code="A1",
                nom="x",
                categorie=self.cd,
                rang=5,
                date_ouverture=date(2019, 6, 1),
            )

        before, after = date(2019, 12, 31), D2020
        self.assertEqual(
            list(Grade.objects.ouvertes(before).values_list("nom", flat=True)), ["Attaché (ancien)"]
        )
        self.assertEqual(
            list(Grade.objects.ouvertes(after).values_list("nom", flat=True)), ["Attaché (réformé)"]
        )
        self.assertEqual(
            sorted(Echelon.objects.ouvertes(before).values_list("grade", "numero")),
            [(self.old.pk, 1), (self.old.pk, 2)],
        )
        self.assertEqual(Echelon.objects.ouvertes(after).filter(grade=new).count(), 3)

    def test_create_correct_and_close_are_audited(self):
        a2 = grade("A2", self.cd, 2)
        step = echelon(a2, 1)
        a2.nom = "Attaché de 2e classe"
        a2.save()
        step.date_fermeture = D2025
        step.save()

        for model, obj, label in (
            ("grade", a2, "A2 — Attaché de 2e classe"),
            ("echelon", step, "A2 — Échelon 1"),
        ):
            with self.subTest(model):
                entries = EntreeAudit.objects.filter(table__model=model, objet_id=obj.pk)
                self.assertEqual(
                    [e.action for e in entries.order_by("id")], ["creation", "modification"]
                )
                self.assertEqual(entries.latest("id").objet_libelle, label)
                self.assertEqual(entries.latest("id").module, "referentiels")


class ReversedDatesTests(TestCase):
    """A closing date before the opening date is a message, not a database error."""

    def test_each_level_reports_the_closing_date(self):
        cd = categorie("CD", 4)
        a1 = grade("A1", cd, 1)
        rows = {
            "catégorie": Categorie(code="X", nom="X", rang=9, date_ouverture=D2020,
                                   date_fermeture=D2015),
            "grade": Grade(code="X", nom="X", categorie=cd, rang=9, date_ouverture=D2020,
                           date_fermeture=D2015),
            "échelon": Echelon(grade=a1, numero=9, date_ouverture=D2020, date_fermeture=D2015),
        }  # fmt: skip
        for level, obj in rows.items():
            with self.subTest(level):
                errors = errors_of(obj.full_clean)
                self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])
                self.assertNotIn("__all__", errors)
