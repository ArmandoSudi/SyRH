"""General parameters. See specs/2026-11-20-general-parameters."""

import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import DEFINITIONS, Parametre, ParametreManquant
from .test_pieces import errors_of, raw

C = Parametre.Cle
D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
D2025 = date(2025, 7, 1)


def parametre(cle, valeur, *, debut=D2015, fin=None):
    return Parametre.objects.create(
        cle=cle, valeur=valeur, date_ouverture=debut, date_fermeture=fin
    )


class ParametreTests(TestCase):
    def test_every_key_has_a_unit_and_bounds(self):
        self.assertEqual(set(DEFINITIONS), set(C.values))
        for definition in DEFINITIONS.values():
            self.assertLess(definition.minimum, definition.maximum)
            self.assertTrue(definition.unite)

    def test_value_is_created_with_its_label(self):
        row = parametre(C.AGE_RETRAITE, 65)
        self.assertEqual(str(row), "Âge de la retraite : 65 ans")
        self.assertEqual(row.unite, "ans")
        self.assertEqual(str(parametre(C.ENFANTS_MAX, 6)),
                         "Nombre maximal d'enfants pris en charge : 6 enfants")  # fmt: skip

    def test_required_fields(self):
        self.assertEqual(
            set(errors_of(Parametre().full_clean)), {"cle", "valeur", "date_ouverture"}
        )

    def test_out_of_bounds_is_reported_on_the_value_with_the_range(self):
        for cle, valeur in ((C.AGE_RETRAITE, 650), (C.AGE_LIMITE_ENFANT, 17), (C.ENFANTS_MAX, 0)):
            with self.subTest(cle=cle, valeur=valeur):
                obj = Parametre(cle=cle, valeur=valeur, date_ouverture=D2015)
                errors = errors_of(obj.full_clean)
                d = DEFINITIONS[cle]
                self.assertEqual(errors["valeur"], [f"Entre {d.minimum} et {d.maximum} {d.unite}."])
                self.assertNotIn("__all__", errors)
                with self.assertRaises(ValidationError):
                    obj.save()

    def test_bounds_themselves_are_accepted(self):
        for cle, d in DEFINITIONS.items():
            for valeur in (d.minimum, d.maximum):
                Parametre(cle=cle, valeur=valeur, date_ouverture=D2015).full_clean()

    def test_ordered_by_key_then_opening_date(self):
        parametre(C.DUREE_CARRIERE, 30)
        parametre(C.ENFANTS_MAX, 6, debut=D2020)
        parametre(C.ENFANTS_MAX, 4, fin=D2020)
        parametre(C.AGE_LIMITE_ENFANT, 25)
        self.assertEqual(
            list(Parametre.objects.values_list("cle", "valeur")),
            [(C.AGE_LIMITE_ENFANT, 25), (C.ENFANTS_MAX, 4), (C.ENFANTS_MAX, 6),
             (C.DUREE_CARRIERE, 30)],
        )  # fmt: skip

    def test_no_delete_permission(self):
        self.assertEqual(Parametre._meta.default_permissions, ("view", "add", "change"))


class ParametreConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D9)."""

    @classmethod
    def setUpTestData(cls):
        parametre(C.AGE_RETRAITE, 65)

    def assert_refused(self, **values):
        values = {"date_ouverture": D2015, **values}
        with self.assertRaises(IntegrityError):
            raw(Parametre, **values)

    def test_unknown_key(self):
        self.assert_refused(cle="age_pivot", valeur=60)

    def test_value_within_its_key_bounds(self):
        for cle, d in DEFINITIONS.items():
            with self.subTest(cle):
                self.assert_refused(cle=cle, valeur=d.minimum - 1, date_ouverture=date(1990, 1, 1))
                self.assert_refused(cle=cle, valeur=d.maximum + 1, date_ouverture=date(1990, 1, 1))
        raw(Parametre, cle=C.DUREE_CARRIERE, valeur=45, date_ouverture=D2015)
        raw(Parametre, cle=C.ENFANTS_MAX, valeur=1, date_ouverture=D2015)

    def test_closing_after_opening(self):
        self.assert_refused(cle=C.DUREE_CARRIERE, valeur=30, date_fermeture=D2015)

    def test_one_value_per_key_per_period(self):
        self.assert_refused(cle=C.AGE_RETRAITE, valeur=60, date_ouverture=D2020)
        raw(Parametre, cle=C.DUREE_CARRIERE, valeur=30, date_ouverture=D2015)  # other key
        parametre(C.ENFANTS_MAX, 4, fin=D2020)
        raw(Parametre, cle=C.ENFANTS_MAX, valeur=6, date_ouverture=D2020)  # consecutive

    def test_overlap_has_a_french_message_in_forms(self):
        obj = Parametre(cle=C.AGE_RETRAITE, valeur=60, date_ouverture=D2020)
        self.assertIn("a déjà une valeur", str(errors_of(obj.full_clean)))

    def test_reversed_dates_report_the_closing_date(self):
        obj = Parametre(cle=C.DUREE_CARRIERE, valeur=30, date_ouverture=D2020,
                        date_fermeture=D2015)  # fmt: skip
        errors = errors_of(obj.full_clean)
        self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])
        self.assertNotIn("__all__", errors)


class ParametreHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.old = parametre(C.ENFANTS_MAX, 4, fin=D2020)
        cls.new = parametre(C.ENFANTS_MAX, 6, debut=D2020)
        parametre(C.AGE_RETRAITE, 65, debut=D2025)

    def test_open_from_opening_day_to_closing_day_excluded(self):
        def values_on(day):
            return set(Parametre.objects.ouvertes(day).values_list("cle", "valeur"))

        self.assertEqual(values_on(date(2014, 12, 31)), set())
        self.assertEqual(values_on(date(2019, 12, 31)), {(C.ENFANTS_MAX, 4)})
        self.assertEqual(values_on(D2020), {(C.ENFANTS_MAX, 6)})
        self.assertEqual(values_on(D2025), {(C.ENFANTS_MAX, 6), (C.AGE_RETRAITE, 65)})

    def test_valeur_au_before_on_and_after_a_change(self):
        self.assertEqual(Parametre.valeur_au(C.ENFANTS_MAX, date(2019, 12, 31)), 4)
        self.assertEqual(Parametre.valeur_au(C.ENFANTS_MAX, D2020), 6)
        self.assertEqual(Parametre.valeur_au(C.ENFANTS_MAX, D2025), 6)

    def test_valeur_au_without_a_value_names_the_key_and_the_date(self):
        with self.assertRaisesMessage(
            ParametreManquant,
            "Aucune valeur du paramètre « Âge de la retraite » au 01/01/2020.",
        ):
            Parametre.valeur_au(C.AGE_RETRAITE, D2020)
        with self.assertRaises(LookupError):
            Parametre.valeur_au(C.DUREE_CARRIERE, D2025)

    def test_key_never_changes_but_value_and_dates_can(self):
        self.new.cle = C.AGE_LIMITE_ENFANT
        self.assertIn("Ne peut pas être modifié", errors_of(self.new.full_clean)["cle"][0])
        with self.assertRaises(ValidationError):
            self.new.save()

        self.new.refresh_from_db()
        self.new.valeur = 5
        self.new.date_fermeture = D2025
        self.new.full_clean()
        self.new.save()
        self.new.refresh_from_db()
        self.assertEqual((self.new.cle, self.new.valeur), (C.ENFANTS_MAX, 5))


class ParametreAuditTests(TestCase):
    def test_create_correct_and_close_are_audited(self):
        row = parametre(C.AGE_RETRAITE, 56)
        row.valeur = 65
        row.save()
        row.date_fermeture = D2025
        row.save()

        entries = EntreeAudit.objects.filter(table__model="parametre", objet_id=row.pk)
        self.assertEqual(entries.count(), 3)
        self.assertEqual(
            set(entries.values_list("module", "objet_libelle")),
            {
                ("referentiels", "Âge de la retraite : 56 ans"),
                ("referentiels", "Âge de la retraite : 65 ans"),
            },
        )


class CleMirrorTests(TestCase):
    """The screen's list of keys matches the model's (general parameters D20)."""

    def test_frontend_list_matches_the_backend(self):
        source = (
            Path(settings.BASE_DIR).parent
            / "frontend/src/features/referentiels/components/parametres.ts"
        ).read_text()
        pairs = [
            (cle, libelle)
            for cle, _, libelle in re.findall(
                r"\{ cle: '([a-z_]+)', libelle: (['\"])(.+?)\2 \}", source
            )
        ]
        self.assertEqual(pairs, [(cle, str(label)) for cle, label in C.choices])
