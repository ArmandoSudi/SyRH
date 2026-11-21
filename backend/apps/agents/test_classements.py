"""Classifications. See specs/2026-11-21-position-history."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.audit.models import EntreeAudit
from apps.referentiels.models import Categorie, Echelon, Grade

from .models import (
    CLASSEMENT_AGENT_FIXED,
    CLASSEMENT_DATE_PRISE,
    HORS_CONTRAT,
    Agent,
    Classement,
)
from .test_affectations import D2015, errors_of
from .test_affectations import Base as ContractsBase


def echelon(grade, numero, debut=D2015, fin=None):
    return Echelon.objects.create(
        grade=grade, numero=numero, date_ouverture=debut, date_fermeture=fin
    )


class Base(ContractsBase):
    """The agents of the assignment tests, with grade A2 and its échelons 1 and 3."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cat = Categorie.objects.create(code="A", nom="Cadres", rang=3, date_ouverture=D2015)
        cls.a2 = Grade.objects.create(
            code="A2", nom="Attaché", categorie=cat, rang=2, date_ouverture=D2015
        )
        cls.e1 = echelon(cls.a2, 1)
        cls.e3 = echelon(cls.a2, 3)

    def unsaved(self, jour, echelon=None, agent=None):
        return Classement(agent=agent or self.agent, echelon=echelon or self.e1, date_effet=jour)

    def classement(self, jour, echelon=None, agent=None):
        row = self.unsaved(jour, echelon, agent)
        row.save()
        return row

    def raw(self, jour, agent=None):
        """Bypass the model, so only the database decides."""
        with transaction.atomic():
            Classement._base_manager.bulk_create([self.unsaved(jour, agent=agent)])


class ClassementTests(Base):
    def test_created_with_its_label(self):
        row = self.classement(date(2020, 3, 1), self.e3)
        self.assertEqual(str(row), "A2 — Échelon 3 depuis le 01/03/2020 — ARPTC/0001/2020")

    def test_grade_and_category_are_read_through_the_echelon(self):
        row = self.classement(date(2020, 3, 1), self.e3)
        self.assertEqual(row.grade, self.a2)
        self.assertEqual(row.grade.categorie.code, "A")
        self.assertNotIn("grade", [field.name for field in Classement._meta.fields])

    def test_required_fields(self):
        self.assertEqual(
            set(errors_of(Classement().full_clean)), {"agent", "echelon", "date_effet"}
        )

    def test_ordered_by_agent_then_date(self):
        second = self.classement(date(2022, 6, 1), self.e3)
        first = self.classement(date(2020, 3, 1))
        self.assertEqual(list(self.agent.classements.all()), [first, second])

    def test_same_date_is_reported_by_full_clean(self):
        self.classement(date(2020, 3, 1))
        row = self.unsaved(date(2020, 3, 1), self.e3)
        self.assertEqual(errors_of(row.full_clean), {"__all__": [CLASSEMENT_DATE_PRISE]})
        self.unsaved(date(2020, 3, 2), self.e3).full_clean()
        self.unsaved(date(2020, 3, 1), agent=self.other).full_clean()

    def test_echelon_must_be_open_on_the_date(self):
        closed = echelon(self.a2, 4, fin=date(2020, 6, 1))
        later = echelon(self.a2, 5, debut=date(2020, 7, 1))
        self.assertEqual(
            errors_of(self.unsaved(date(2020, 6, 1), closed).full_clean),
            {"echelon": ["L'échelon « A2 — Échelon 4 » n'est pas ouvert le 01/06/2020."]},
        )
        self.assertIn("echelon", errors_of(self.unsaved(date(2020, 6, 30), later).full_clean))
        # Open on the date; a later closing is not checked (D9).
        self.unsaved(date(2020, 5, 31), closed).full_clean()
        self.unsaved(date(2020, 7, 1), later).full_clean()
        with self.assertRaises(ValidationError):
            self.classement(date(2020, 6, 1), closed)

    def test_date_must_fall_inside_a_contract(self):
        for jour in (date(2020, 2, 29), date(2021, 3, 1), date(2022, 5, 31)):
            with self.subTest(jour=jour):
                self.assertEqual(
                    errors_of(self.unsaved(jour).full_clean), {"date_effet": [HORS_CONTRAT]}
                )
        for jour in (date(2020, 3, 1), date(2021, 2, 28), date(2022, 6, 1), date(2040, 1, 1)):
            with self.subTest(jour=jour):
                self.unsaved(jour).full_clean()
        with self.assertRaises(ValidationError):
            self.classement(date(2021, 3, 1))

    def test_corrections_are_accepted_but_the_agent_is_fixed(self):
        row = self.classement(date(2020, 3, 1))
        row.echelon, row.date_effet = self.e3, date(2020, 4, 1)
        row.full_clean()
        row.save()

        row.agent = self.other
        self.assertEqual(errors_of(row.full_clean)["agent"], [CLASSEMENT_AGENT_FIXED])
        with self.assertRaises(ValidationError):
            row.save()

    def test_never_deleted(self):
        row = self.classement(date(2020, 3, 1))
        with self.assertRaises(PermissionError):
            row.delete()
        self.assertTrue(Classement.objects.filter(pk=row.pk).exists())
        self.assertEqual(Classement._meta.default_permissions, ("view", "add", "change"))


class ClassementConstraintTests(Base):
    """Rules on the rows themselves, enforced by PostgreSQL (D3, D13)."""

    def test_two_rows_on_the_same_date_are_refused(self):
        self.raw(date(2020, 3, 1))
        with self.assertRaises(IntegrityError):
            self.raw(date(2020, 3, 1))

    def test_other_dates_and_other_agents_are_accepted(self):
        self.raw(date(2020, 3, 1))
        self.raw(date(2020, 3, 2))
        self.raw(date(2020, 3, 1), agent=self.other)
        self.assertEqual(Classement.objects.count(), 3)


class ClassementAuTests(Base):
    def test_classification_in_force_on_a_day(self):
        self.assertIsNone(self.agent.classement_au(date(2030, 1, 1)))
        second = self.classement(date(2022, 6, 1), self.e3)
        first = self.classement(date(2020, 3, 1))
        cases = {
            date(2020, 2, 29): None, date(2020, 3, 1): first, date(2021, 12, 31): first,
            date(2022, 6, 1): second, date(2040, 1, 1): second,
        }  # fmt: skip
        prefetched = Agent.objects.prefetch_related("classements").get(pk=self.agent.pk)
        for jour, expected in cases.items():
            with self.subTest(jour=jour):
                self.assertEqual(self.agent.classement_au(jour), expected)
                with self.assertNumQueries(0):
                    self.assertEqual(prefetched.classement_au(jour), expected)

    def test_unsaved_agent_has_none(self):
        self.assertIsNone(Agent().classement_au(date(2020, 3, 1)))


class ClassementAuditTests(Base):
    def test_create_and_correct_are_audited_with_label_and_author(self):
        user = get_user_model().objects.create_user("carriere", password="x")
        row = Classement.objects.create(
            agent=self.agent, echelon=self.e1, date_effet=date(2020, 3, 1),
            cree_par=user, modifie_par=user,
        )  # fmt: skip
        row.echelon = self.e3
        row.save()

        entries = EntreeAudit.objects.filter(table__model="classement", objet_id=row.pk)
        self.assertEqual(
            set(entries.values_list("action", "module", "objet_libelle", "auteur")),
            {
                ("creation", "agents",
                 "A2 — Échelon 1 depuis le 01/03/2020 — ARPTC/0001/2020", user.pk),
                ("modification", "agents",
                 "A2 — Échelon 3 depuis le 01/03/2020 — ARPTC/0001/2020", user.pk),
            },
        )  # fmt: skip
