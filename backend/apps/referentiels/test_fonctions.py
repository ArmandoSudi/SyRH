"""Fonctions: job functions. See specs/2026-11-18-fonctions."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import Fonction

D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
D2025 = date(2025, 7, 1)

RESP = Fonction.Nature.RESPONSABILITE
EXEC = Fonction.Nature.EXECUTION


def fonction(code, nom=None, nature=EXEC, *, debut=D2015, fin=None):
    return Fonction.objects.create(
        code=code,
        nom=nom or f"Fonction {code}",
        nature=nature,
        date_ouverture=debut,
        date_fermeture=fin,
    )


def raw(**values):
    """Bypass the model, so only the database decides."""
    values = {"nom": "x", "nature": EXEC, "date_ouverture": D2015, **values}
    with transaction.atomic():
        Fonction._base_manager.bulk_create([Fonction(**values)])


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


class FonctionTests(TestCase):
    def test_fonction_is_created_with_its_label(self):
        cs = fonction("cs ", "Chef de service", RESP)

        cs.refresh_from_db()
        self.assertEqual(cs.code, "CS")
        self.assertEqual(str(cs), "CS — Chef de service")
        self.assertEqual(cs.get_nature_display(), "Responsabilité")

    def test_code_in_capitals_through_full_clean(self):
        obj = Fonction(code=" jur", nom="Juriste", nature=EXEC, date_ouverture=D2015)
        obj.full_clean()
        self.assertEqual(obj.code, "JUR")

    def test_required_fields(self):
        errors = errors_of(Fonction().full_clean)
        self.assertEqual(set(errors), {"code", "nom", "nature", "date_ouverture"})

    def test_responsabilite_first_then_by_name(self):
        fonction("JUR", "Juriste")
        fonction("CS", "Chef de service", RESP)
        fonction("CPT", "Comptable")
        fonction("DIR", "Directeur", RESP)

        self.assertEqual(
            list(Fonction.objects.values_list("code", flat=True)), ["CS", "DIR", "CPT", "JUR"]
        )

    def test_same_name_is_accepted(self):
        fonction("A1", "Assistant")
        fonction("A2", "Assistant")
        self.assertEqual(Fonction.objects.filter(nom="Assistant").count(), 2)

    def test_no_delete_permission(self):
        self.assertEqual(Fonction._meta.default_permissions, ("view", "add", "change"))


class FonctionConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D8)."""

    @classmethod
    def setUpTestData(cls):
        cls.jur = fonction("JUR", "Juriste")

    def assert_refused(self, **values):
        with self.assertRaises(IntegrityError):
            raw(**values)

    def test_nature_is_one_of_two(self):
        self.assert_refused(code="X1", nature="chef")

    def test_closing_after_opening(self):
        self.assert_refused(code="X2", date_fermeture=D2015)
        self.assert_refused(code="X3", date_fermeture=date(2014, 1, 1))

    def test_code_unique_over_overlapping_periods(self):
        self.assert_refused(code="JUR", date_ouverture=D2020)
        fonction("OLD", fin=D2020)
        # Consecutive periods may share a code: the closing day is the first day closed.
        raw(code="OLD", date_ouverture=D2020)
        self.assert_refused(code="OLD", date_ouverture=date(2019, 12, 31))

    def test_constraints_have_french_messages_in_forms(self):
        cases = {
            "porte déjà ce code": Fonction(
                code="jur", nom="Bis", nature=EXEC, date_ouverture=D2020
            ),
            "postérieure à la date d'ouverture": Fonction(
                code="F", nom="F", nature=EXEC, date_ouverture=D2020, date_fermeture=D2020
            ),
        }
        for fragment, obj in cases.items():
            with self.subTest(fragment):
                self.assertIn(fragment, str(errors_of(obj.full_clean)))


class FonctionHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fonction("JUR", "Juriste")
        fonction("CE", "Chargé d'études", fin=D2020)
        fonction("CE", "Analyste", debut=D2020)
        fonction("LATER", debut=D2025)

    def names_on(self, day):
        return set(Fonction.objects.ouvertes(day).values_list("nom", flat=True))

    def test_open_from_opening_day_to_closing_day_excluded(self):
        self.assertEqual(self.names_on(date(2014, 12, 31)), set())
        self.assertEqual(self.names_on(D2015), {"Juriste", "Chargé d'études"})
        self.assertEqual(self.names_on(date(2019, 12, 31)), {"Juriste", "Chargé d'études"})
        self.assertEqual(self.names_on(D2020), {"Juriste", "Analyste"})
        self.assertEqual(self.names_on(D2025), {"Juriste", "Analyste", "Fonction LATER"})

    def test_rename_keeps_the_old_name_at_earlier_dates(self):
        jur = Fonction.objects.get(code="JUR")
        jur.date_fermeture = D2025
        jur.save()
        fonction("JUR", "Conseiller juridique", debut=D2025)

        self.assertIn("Juriste", self.names_on(date(2025, 6, 30)))
        self.assertNotIn("Conseiller juridique", self.names_on(date(2025, 6, 30)))
        self.assertIn("Conseiller juridique", self.names_on(D2025))
        self.assertNotIn("Juriste", self.names_on(D2025))


class FonctionAuditTests(TestCase):
    def test_create_correct_and_close_are_audited(self):
        jur = fonction("JUR", "Jurist")
        jur.nom = "Juriste"
        jur.save()
        jur.date_fermeture = D2025
        jur.save()

        entries = EntreeAudit.objects.filter(table__model="fonction", objet_id=jur.pk)
        self.assertEqual(entries.count(), 3)
        self.assertEqual(
            set(entries.values_list("module", "objet_libelle")),
            {("referentiels", "JUR — Jurist"), ("referentiels", "JUR — Juriste")},
        )
