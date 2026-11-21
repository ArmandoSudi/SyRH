"""Contracts. See specs/2026-11-21-contract."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.audit.models import EntreeAudit
from apps.referentiels.models import TypeContrat

from .models import (
    CONTRAT_AGENT_FIXED,
    CONTRAT_OVERLAP,
    ESSAI_HORS_CONTRAT,
    ESSAI_INTERDIT,
    FIN_AVANT_DEBUT,
    FIN_INTERDITE,
    FIN_OBLIGATOIRE,
    Agent,
    Contrat,
)

D2015 = date(2015, 1, 1)


def agent(matricule="ARPTC/0001/2020", nom="Mukendi"):
    return Agent.objects.create(
        matricule=matricule, nom=nom, sexe="M", date_naissance=date(1985, 3, 14),
        lieu_naissance="Kinshasa",
    )  # fmt: skip


def type_contrat(code, duree_determinee, periode_essai, debut=D2015, fin=None):
    return TypeContrat.objects.create(
        code=code, nom=code, duree_determinee=duree_determinee, periode_essai=periode_essai,
        date_ouverture=debut, date_fermeture=fin,
    )  # fmt: skip


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cdi = type_contrat("CDI", False, True)
        cls.cdd = type_contrat("CDD", True, True)
        cls.stage = type_contrat("STG", True, False)
        cls.agent = agent()

    def contrat(self, type_contrat, debut, fin=None, essai=None, agent=None):
        return Contrat.objects.create(
            agent=agent or self.agent, type_contrat=type_contrat, date_debut=debut,
            date_fin=fin, fin_periode_essai=essai,
        )  # fmt: skip

    def unsaved(self, type_contrat, debut, fin=None, essai=None, agent=None):
        return Contrat(
            agent=agent or self.agent, type_contrat=type_contrat, date_debut=debut,
            date_fin=fin, fin_periode_essai=essai,
        )  # fmt: skip

    def raw(self, type_contrat, debut, fin=None, essai=None, agent=None):
        """Bypass the model, so only the database decides."""
        with transaction.atomic():
            Contrat._base_manager.bulk_create(
                [self.unsaved(type_contrat, debut, fin, essai, agent)]
            )


class ContratTests(Base):
    def test_created_with_its_label(self):
        cdd = self.contrat(self.cdd, date(2020, 3, 1), date(2021, 2, 28))
        cdi = self.contrat(self.cdi, date(2021, 3, 1))
        self.assertEqual(str(cdd), "CDD du 01/03/2020 au 28/02/2021 — ARPTC/0001/2020")
        self.assertEqual(str(cdi), "CDI depuis le 01/03/2021 — ARPTC/0001/2020")

    def test_required_fields(self):
        self.assertEqual(
            set(errors_of(Contrat().full_clean)), {"agent", "type_contrat", "date_debut"}
        )

    def test_ordered_by_agent_then_start(self):
        second = self.contrat(self.cdi, date(2021, 3, 1))
        first = self.contrat(self.cdd, date(2020, 3, 1), date(2021, 2, 28))
        self.assertEqual(list(self.agent.contrats.all()), [first, second])

    def test_reversed_dates_are_reported_on_their_field(self):
        errors = errors_of(self.unsaved(self.cdd, date(2020, 3, 1), date(2020, 2, 1)).full_clean)
        self.assertIn(FIN_AVANT_DEBUT, errors["date_fin"])
        self.assertNotIn("__all__", errors)
        for essai in (date(2020, 2, 29), date(2021, 3, 1)):
            with self.subTest(essai=essai):
                row = self.unsaved(self.cdd, date(2020, 3, 1), date(2021, 2, 28), essai)
                self.assertEqual(
                    errors_of(row.full_clean), {"fin_periode_essai": [ESSAI_HORS_CONTRAT]}
                )
        with self.assertRaises(ValidationError):
            self.contrat(self.cdd, date(2020, 3, 1), date(2020, 2, 1))

    def test_probation_on_its_last_days_is_accepted(self):
        for essai in (date(2020, 3, 1), date(2021, 2, 28)):
            self.unsaved(self.cdd, date(2020, 3, 1), date(2021, 2, 28), essai).full_clean()
        self.unsaved(self.cdi, date(2020, 3, 1), essai=date(2020, 8, 31)).full_clean()

    def test_end_date_follows_the_type(self):
        self.assertEqual(
            errors_of(self.unsaved(self.cdd, date(2020, 3, 1)).full_clean),
            {"date_fin": [FIN_OBLIGATOIRE]},
        )
        self.assertEqual(
            errors_of(self.unsaved(self.cdi, date(2020, 3, 1), date(2021, 2, 28)).full_clean),
            {"date_fin": [FIN_INTERDITE]},
        )
        with self.assertRaises(ValidationError):
            self.contrat(self.cdd, date(2020, 3, 1))

    def test_probation_follows_the_type(self):
        row = self.unsaved(self.stage, date(2020, 3, 1), date(2020, 8, 31), date(2020, 4, 30))
        self.assertEqual(errors_of(row.full_clean), {"fin_periode_essai": [ESSAI_INTERDIT]})
        self.unsaved(self.stage, date(2020, 3, 1), date(2020, 8, 31)).full_clean()

    def test_type_must_be_open_on_the_start_date(self):
        retired = type_contrat("APP", True, False, fin=date(2023, 1, 1))
        later = type_contrat("NEW", True, False, debut=date(2025, 1, 1))
        for type_, debut in ((retired, date(2023, 1, 1)), (later, date(2024, 12, 31))):
            with self.subTest(type=type_.code):
                row = self.unsaved(type_, debut, date(2025, 6, 30))
                self.assertIn("type_contrat", errors_of(row.full_clean))
        self.unsaved(retired, date(2022, 12, 31), date(2023, 6, 30)).full_clean()

    def test_overlap_is_reported_by_full_clean(self):
        self.contrat(self.cdd, date(2020, 3, 1), date(2021, 2, 28))
        row = self.unsaved(self.cdi, date(2021, 2, 28))
        self.assertEqual(errors_of(row.full_clean), {"__all__": [CONTRAT_OVERLAP]})
        self.unsaved(self.cdi, date(2021, 3, 1)).full_clean()

    def test_corrections_are_accepted_but_the_agent_is_fixed(self):
        row = self.contrat(self.cdd, date(2020, 3, 1), date(2021, 2, 28))
        row.date_fin = date(2021, 3, 31)
        row.fin_periode_essai = date(2020, 5, 31)
        row.full_clean()
        row.save()

        row.agent = agent("ARPTC/0002/2020", "Nsimba")
        self.assertEqual(errors_of(row.full_clean)["agent"], [CONTRAT_AGENT_FIXED])
        with self.assertRaises(ValidationError):
            row.save()

    def test_never_deleted(self):
        row = self.contrat(self.cdi, date(2020, 3, 1))
        with self.assertRaises(PermissionError):
            row.delete()
        self.assertTrue(Contrat.objects.filter(pk=row.pk).exists())
        self.assertEqual(Contrat._meta.default_permissions, ("view", "add", "change"))


class ContratConstraintTests(Base):
    """Rules on the rows themselves, enforced by PostgreSQL (D2, D12)."""

    def test_reversed_dates_are_refused(self):
        with self.assertRaises(IntegrityError):
            self.raw(self.cdd, date(2020, 3, 1), date(2020, 2, 29))

    def test_probation_outside_the_contract_is_refused(self):
        for essai in (date(2020, 2, 29), date(2021, 3, 1)):
            with self.subTest(essai=essai), self.assertRaises(IntegrityError):
                self.raw(self.cdd, date(2020, 3, 1), date(2021, 2, 28), essai)
        with self.assertRaises(IntegrityError):
            self.raw(self.cdi, date(2020, 3, 1), essai=date(2020, 2, 1))

    def test_overlapping_contracts_are_refused(self):
        self.raw(self.cdd, date(2020, 3, 1), date(2021, 2, 28))
        overlapping = (
            (date(2021, 2, 28), None),  # starts on the other's last day
            (date(2020, 1, 1), date(2020, 3, 1)),  # ends on the other's first day
            (date(2020, 6, 1), date(2020, 7, 1)),  # inside
            (date(2019, 1, 1), None),  # open-ended, covering it
        )
        for debut, fin in overlapping:
            with self.subTest(debut=debut, fin=fin), self.assertRaises(IntegrityError):
                self.raw(self.cdi, debut, fin)

    def test_open_ended_contract_refuses_any_later_one(self):
        self.raw(self.cdi, date(2020, 3, 1))
        with self.assertRaises(IntegrityError):
            self.raw(self.cdd, date(2030, 1, 1), date(2030, 6, 30))

    def test_consecutive_contracts_a_gap_and_other_agents_are_accepted(self):
        self.raw(self.cdd, date(2020, 3, 1), date(2021, 2, 28))
        self.raw(self.cdd, date(2021, 3, 1), date(2022, 2, 28))
        self.raw(self.cdi, date(2022, 6, 1))
        self.raw(self.cdi, date(2020, 3, 1), agent=agent("ARPTC/0002/2020", "Nsimba"))
        self.assertEqual(Contrat.objects.count(), 4)


class HiringDateTests(Base):
    def test_hiring_date_is_the_first_start_whatever_the_order(self):
        self.assertIsNone(self.agent.date_engagement)
        self.contrat(self.cdi, date(2022, 6, 1))
        self.contrat(self.cdd, date(2020, 3, 1), date(2021, 2, 28))
        self.assertEqual(Agent.objects.get(pk=self.agent.pk).date_engagement, date(2020, 3, 1))
        prefetched = Agent.objects.prefetch_related("contrats").get(pk=self.agent.pk)
        with self.assertNumQueries(0):
            self.assertEqual(prefetched.date_engagement, date(2020, 3, 1))

    def test_contract_in_force_on_a_day(self):
        cdd = self.contrat(self.cdd, date(2020, 3, 1), date(2021, 2, 28))
        cdi = self.contrat(self.cdi, date(2022, 6, 1))
        cases = {
            date(2020, 2, 29): None, date(2020, 3, 1): cdd, date(2020, 9, 1): cdd,
            date(2021, 2, 28): cdd, date(2021, 3, 1): None, date(2022, 6, 1): cdi,
            date(2040, 1, 1): cdi,
        }  # fmt: skip
        prefetched = Agent.objects.prefetch_related("contrats").get(pk=self.agent.pk)
        for jour, expected in cases.items():
            with self.subTest(jour=jour):
                self.assertEqual(self.agent.contrat_au(jour), expected)
                self.assertEqual(prefetched.contrat_au(jour), expected)


class ContratAuditTests(Base):
    def test_create_and_correct_are_audited_with_label_and_author(self):
        user = get_user_model().objects.create_user("carriere", password="x")
        row = Contrat.objects.create(
            agent=self.agent, type_contrat=self.cdd, date_debut=date(2020, 3, 1),
            date_fin=date(2021, 2, 28), cree_par=user, modifie_par=user,
        )  # fmt: skip
        row.date_fin = date(2021, 3, 31)
        row.save()

        entries = EntreeAudit.objects.filter(table__model="contrat", objet_id=row.pk)
        self.assertEqual(
            set(entries.values_list("action", "module", "objet_libelle", "auteur")),
            {
                ("creation", "agents", "CDD du 01/03/2020 au 28/02/2021 — ARPTC/0001/2020",
                 user.pk),
                ("modification", "agents", "CDD du 01/03/2020 au 31/03/2021 — ARPTC/0001/2020",
                 user.pk),
            },
        )  # fmt: skip
