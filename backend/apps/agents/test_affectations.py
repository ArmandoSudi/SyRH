"""Assignments. See specs/2026-11-21-position-history."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.audit.models import EntreeAudit
from apps.referentiels.models import Fonction, Site, TypeContrat
from apps.referentiels.models import UniteOrganisationnelle as Unite

from .models import (
    AFFECTATION_AGENT_FIXED,
    AFFECTATION_DATE_PRISE,
    HORS_CONTRAT,
    Affectation,
    Agent,
    Contrat,
)

D2015 = date(2015, 1, 1)


def agent(matricule="ARPTC/0001/2020", nom="Mukendi"):
    return Agent.objects.create(
        matricule=matricule, nom=nom, sexe="M", date_naissance=date(1985, 3, 14),
        lieu_naissance="Kinshasa",
    )  # fmt: skip


def unite(code, type_, parent=None, debut=D2015, fin=None):
    return Unite.objects.create(
        code=code, nom=f"Unité {code}", type=type_, parent=parent,
        site=Site.objects.get(code="KIN"), date_ouverture=debut, date_fermeture=fin,
    )  # fmt: skip


def fonction(code, nom, debut=D2015, fin=None):
    return Fonction.objects.create(
        code=code, nom=nom, nature=Fonction.Nature.EXECUTION, date_ouverture=debut,
        date_fermeture=fin,
    )  # fmt: skip


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


class Base(TestCase):
    """One agent under a CDD from 01/03/2020 to 28/02/2021, then a CDI from
    01/06/2022 after a gap."""

    @classmethod
    def setUpTestData(cls):
        Site.objects.create(code="KIN", nom="Kinshasa", ville="Kinshasa", siege=True)
        cls.drh = unite("DRH", "direction")
        cls.dep = unite("DGC", "departement", cls.drh)
        cls.svc = unite("SCAR", "service", cls.dep)
        cls.bur = unite("BADM", "bureau", cls.svc)
        cls.chef = fonction("CS", "Chef de service")
        cls.juriste = fonction("JUR", "Juriste")
        cls.agent = agent()
        cdi = TypeContrat.objects.create(
            code="CDI", nom="CDI", duree_determinee=False, periode_essai=True,
            date_ouverture=D2015,
        )  # fmt: skip
        cdd = TypeContrat.objects.create(
            code="CDD", nom="CDD", duree_determinee=True, periode_essai=True,
            date_ouverture=D2015,
        )  # fmt: skip
        for a in (cls.agent, agent("ARPTC/0002/2020", "Nsimba")):
            Contrat.objects.create(
                agent=a, type_contrat=cdd, date_debut=date(2020, 3, 1), date_fin=date(2021, 2, 28)
            )
            Contrat.objects.create(agent=a, type_contrat=cdi, date_debut=date(2022, 6, 1))
        cls.other = Agent.objects.get(matricule="ARPTC/0002/2020")

    def unsaved(self, jour, unite=None, fonction=None, agent=None):
        return Affectation(
            agent=agent or self.agent, unite=unite or self.svc, fonction=fonction or self.chef,
            date_effet=jour,
        )  # fmt: skip

    def affectation(self, jour, unite=None, fonction=None, agent=None):
        row = self.unsaved(jour, unite, fonction, agent)
        row.save()
        return row

    def raw(self, jour, agent=None):
        """Bypass the model, so only the database decides."""
        with transaction.atomic():
            Affectation._base_manager.bulk_create([self.unsaved(jour, agent=agent)])


class AffectationTests(Base):
    def test_created_with_its_label(self):
        row = self.affectation(date(2020, 3, 1), self.drh)
        self.assertEqual(str(row), "DRH · Chef de service depuis le 01/03/2020 — ARPTC/0001/2020")

    def test_required_fields(self):
        self.assertEqual(
            set(errors_of(Affectation().full_clean)), {"agent", "unite", "fonction", "date_effet"}
        )

    def test_every_unit_level_is_accepted(self):
        for unite_ in (self.drh, self.dep, self.svc, self.bur):
            with self.subTest(unite=unite_.code):
                self.unsaved(date(2020, 3, 1), unite_).full_clean()

    def test_ordered_by_agent_then_date(self):
        second = self.affectation(date(2022, 6, 1))
        first = self.affectation(date(2020, 3, 1))
        self.assertEqual(list(self.agent.affectations.all()), [first, second])

    def test_same_date_is_reported_by_full_clean(self):
        self.affectation(date(2020, 3, 1))
        row = self.unsaved(date(2020, 3, 1), fonction=self.juriste)
        self.assertEqual(errors_of(row.full_clean), {"__all__": [AFFECTATION_DATE_PRISE]})
        self.unsaved(date(2020, 3, 2), fonction=self.juriste).full_clean()
        self.unsaved(date(2020, 3, 1), agent=self.other).full_clean()

    def test_unit_and_function_must_be_open_on_the_date(self):
        closed = unite("SOLD", "service", self.dep, fin=date(2020, 6, 1))
        later = fonction("NEW", "Nouvelle", debut=date(2020, 7, 1))
        self.assertEqual(
            set(errors_of(self.unsaved(date(2020, 6, 1), closed, later).full_clean)),
            {"unite", "fonction"},
        )
        message = errors_of(self.unsaved(date(2020, 6, 1), closed).full_clean)["unite"]
        self.assertEqual(message, ["L'unité « SOLD » n'est pas ouverte le 01/06/2020."])
        # Open on the date; closing or opening around it is not checked (D9).
        self.unsaved(date(2020, 5, 31), closed).full_clean()
        self.unsaved(date(2020, 7, 1), fonction=later).full_clean()
        with self.assertRaises(ValidationError):
            self.affectation(date(2020, 6, 1), closed)

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
            self.affectation(date(2021, 3, 1))

    def test_corrections_are_accepted_but_the_agent_is_fixed(self):
        row = self.affectation(date(2020, 3, 1))
        row.unite, row.fonction, row.date_effet = self.bur, self.juriste, date(2020, 4, 1)
        row.full_clean()
        row.save()

        row.agent = self.other
        self.assertEqual(errors_of(row.full_clean)["agent"], [AFFECTATION_AGENT_FIXED])
        with self.assertRaises(ValidationError):
            row.save()

    def test_never_deleted(self):
        row = self.affectation(date(2020, 3, 1))
        with self.assertRaises(PermissionError):
            row.delete()
        self.assertTrue(Affectation.objects.filter(pk=row.pk).exists())
        self.assertEqual(Affectation._meta.default_permissions, ("view", "add", "change"))


class AffectationConstraintTests(Base):
    """Rules on the rows themselves, enforced by PostgreSQL (D3, D13)."""

    def test_two_rows_on_the_same_date_are_refused(self):
        self.raw(date(2020, 3, 1))
        with self.assertRaises(IntegrityError):
            self.raw(date(2020, 3, 1))

    def test_other_dates_and_other_agents_are_accepted(self):
        self.raw(date(2020, 3, 1))
        self.raw(date(2020, 3, 2))
        self.raw(date(2020, 3, 1), agent=self.other)
        self.assertEqual(Affectation.objects.count(), 3)


class AffectationAuTests(Base):
    def test_assignment_in_force_on_a_day(self):
        self.assertIsNone(self.agent.affectation_au(date(2030, 1, 1)))
        second = self.affectation(date(2022, 6, 1), fonction=self.juriste)
        first = self.affectation(date(2020, 3, 1))
        cases = {
            date(2020, 2, 29): None, date(2020, 3, 1): first, date(2021, 12, 31): first,
            date(2022, 6, 1): second, date(2040, 1, 1): second,
        }  # fmt: skip
        prefetched = Agent.objects.prefetch_related("affectations").get(pk=self.agent.pk)
        for jour, expected in cases.items():
            with self.subTest(jour=jour):
                self.assertEqual(self.agent.affectation_au(jour), expected)
                with self.assertNumQueries(0):
                    self.assertEqual(prefetched.affectation_au(jour), expected)

    def test_unsaved_agent_has_none(self):
        self.assertIsNone(Agent().affectation_au(date(2020, 3, 1)))


class AffectationAuditTests(Base):
    def test_create_and_correct_are_audited_with_label_and_author(self):
        user = get_user_model().objects.create_user("carriere", password="x")
        row = Affectation.objects.create(
            agent=self.agent, unite=self.svc, fonction=self.chef, date_effet=date(2020, 3, 1),
            cree_par=user, modifie_par=user,
        )  # fmt: skip
        row.fonction = self.juriste
        row.save()

        entries = EntreeAudit.objects.filter(table__model="affectation", objet_id=row.pk)
        self.assertEqual(
            set(entries.values_list("action", "module", "objet_libelle", "auteur")),
            {
                ("creation", "agents",
                 "SCAR · Chef de service depuis le 01/03/2020 — ARPTC/0001/2020", user.pk),
                ("modification", "agents",
                 "SCAR · Juriste depuis le 01/03/2020 — ARPTC/0001/2020", user.pk),
            },
        )  # fmt: skip
