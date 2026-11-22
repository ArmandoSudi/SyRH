"""Bank accounts. See specs/2026-11-21-bank-account."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.audit.models import EntreeAudit
from apps.referentiels.models import Banque

from .models import (
    COMPTE_AGENT_FIXED,
    COMPTE_DATE_PRISE,
    NUMERO_HELP,
    NUMERO_PRIS,
    Agent,
    CompteBancaire,
)
from .test_affectations import D2015, agent, errors_of

NUMERO = "05100 0001234"


class Base(TestCase):
    """Two agents without contract (D10: none is needed) and two banks."""

    @classmethod
    def setUpTestData(cls):
        cls.agent = agent()
        cls.other = agent("ARPTC/0002/2020", "Nsimba")
        cls.bcf = Banque.objects.create(code="BCF", nom="Banque du Fleuve", date_ouverture=D2015)
        cls.bik = Banque.objects.create(code="BIK", nom="Banque de Kinshasa", date_ouverture=D2015)

    def unsaved(self, jour, numero=NUMERO, banque=None, agent=None):
        return CompteBancaire(
            agent=agent or self.agent, banque=banque or self.bcf, numero=numero, date_effet=jour
        )

    def compte(self, jour, numero=NUMERO, banque=None, agent=None):
        row = self.unsaved(jour, numero, banque, agent)
        row.save()
        return row

    def raw(self, jour, numero=NUMERO, banque=None, agent=None):
        """Bypass the model, so only the database decides."""
        with transaction.atomic():
            CompteBancaire._base_manager.bulk_create([self.unsaved(jour, numero, banque, agent)])


class CompteBancaireTests(Base):
    def test_created_with_its_label(self):
        row = self.compte(date(2021, 3, 1))
        self.assertEqual(str(row), "BCF — 05100 0001234 depuis le 01/03/2021 — ARPTC/0001/2020")

    def test_required_fields(self):
        self.assertEqual(
            set(errors_of(CompteBancaire().full_clean)), {"agent", "banque", "numero", "date_effet"}
        )

    def test_ordered_by_agent_then_date(self):
        second = self.compte(date(2022, 6, 1), "222222", self.bik)
        first = self.compte(date(2020, 3, 1))
        self.assertEqual(list(self.agent.comptes_bancaires.all()), [first, second])

    def test_number_is_trimmed_and_put_in_capitals(self):
        row = self.unsaved(date(2021, 3, 1), "  ab-0012 34  ")
        row.full_clean()
        self.assertEqual(row.numero, "AB-0012 34")
        row = self.compte(date(2021, 4, 1), " cd12345 ")
        self.assertEqual(CompteBancaire.objects.get(pk=row.pk).numero, "CD12345")

    def test_number_format(self):
        for numero in ("1234", "1" * 35, "12_345", "12.345", "-1234", "1234-", "ÉCU12345"):
            with self.subTest(numero=numero):
                self.assertEqual(
                    errors_of(self.unsaved(date(2021, 3, 1), numero).full_clean),
                    {"numero": [NUMERO_HELP]},
                )
        for numero in ("12-AB", "1" * 34, "CD05 1000 0123 4567 8901 23"):
            with self.subTest(numero=numero):
                self.unsaved(date(2021, 3, 1), numero).full_clean()
        with self.assertRaises(ValidationError):
            self.compte(date(2021, 3, 1), "1234")

    def test_same_date_is_reported_by_full_clean(self):
        self.compte(date(2021, 3, 1))
        row = self.unsaved(date(2021, 3, 1), "999999", self.bik)
        self.assertEqual(errors_of(row.full_clean), {"__all__": [COMPTE_DATE_PRISE]})
        self.unsaved(date(2021, 3, 2), "999999", self.bik).full_clean()
        self.unsaved(date(2021, 3, 1), "999999", agent=self.other).full_clean()

    def test_number_held_by_another_agent_is_reported_on_numero(self):
        self.compte(date(2021, 3, 1))
        row = self.unsaved(date(2022, 1, 1), " 05100 0001234", agent=self.other)
        self.assertEqual(errors_of(row.full_clean), {"numero": [NUMERO_PRIS]})
        with self.assertRaises(ValidationError):
            row.save()
        # Same number at another bank; the same agent back to an old account.
        self.unsaved(date(2022, 1, 1), NUMERO, self.bik, self.other).full_clean()
        self.compte(date(2022, 1, 1), "777777")
        self.compte(date(2023, 1, 1))

    def test_bank_must_be_open_on_the_date(self):
        closed = Banque.objects.create(
            code="OLD", nom="Ancienne", date_ouverture=D2015, date_fermeture=date(2020, 6, 1)
        )
        later = Banque.objects.create(code="NEW", nom="Nouvelle", date_ouverture=date(2020, 7, 1))
        self.assertEqual(
            errors_of(self.unsaved(date(2020, 6, 1), banque=closed).full_clean),
            {"banque": ["La banque « OLD » n'est pas ouverte le 01/06/2020."]},
        )
        self.assertIn("banque", errors_of(self.unsaved(date(2020, 6, 30), banque=later).full_clean))
        # Open on the date; a later closing is not checked (D9).
        self.unsaved(date(2020, 5, 31), banque=closed).full_clean()
        self.unsaved(date(2020, 7, 1), banque=later).full_clean()
        with self.assertRaises(ValidationError):
            self.compte(date(2020, 6, 1), banque=closed)

    def test_any_date_is_accepted_without_a_contract(self):
        self.assertFalse(self.agent.contrats.exists())
        for jour in (date(2015, 1, 1), date(2040, 1, 1)):
            with self.subTest(jour=jour):
                self.unsaved(jour).full_clean()

    def test_corrections_are_accepted_but_the_agent_is_fixed(self):
        row = self.compte(date(2021, 3, 1))
        row.banque, row.numero, row.date_effet = self.bik, "888888", date(2021, 4, 1)
        row.full_clean()
        row.save()

        row.agent = self.other
        self.assertEqual(errors_of(row.full_clean)["agent"], [COMPTE_AGENT_FIXED])
        with self.assertRaises(ValidationError):
            row.save()

    def test_never_deleted(self):
        row = self.compte(date(2021, 3, 1))
        with self.assertRaises(PermissionError):
            row.delete()
        self.assertTrue(CompteBancaire.objects.filter(pk=row.pk).exists())
        self.assertEqual(CompteBancaire._meta.default_permissions, ("view", "add", "change"))


class CompteBancaireConstraintTests(Base):
    """Rules on the rows themselves, enforced by PostgreSQL (D3, D7, D8, D12)."""

    def test_two_rows_on_the_same_date_are_refused(self):
        self.raw(date(2021, 3, 1))
        with self.assertRaises(IntegrityError):
            self.raw(date(2021, 3, 1), "999999", self.bik)

    def test_bad_numbers_are_refused(self):
        for numero in ("abcde", "1234", "1" * 35, " 12345", "12345 ", "12/345"):
            with self.subTest(numero=numero), self.assertRaises(IntegrityError):
                self.raw(date(2021, 3, 1), numero)

    def test_a_bank_and_number_belong_to_one_agent(self):
        self.raw(date(2021, 3, 1))
        with self.assertRaises(IntegrityError):
            self.raw(date(2022, 1, 1), agent=self.other)

    def test_accepted_rows(self):
        self.raw(date(2021, 3, 1))
        self.raw(date(2022, 1, 1), "777777")
        self.raw(date(2023, 1, 1))  # back to the old account
        self.raw(date(2021, 3, 1), banque=self.bik, agent=self.other)  # same number, other bank
        self.assertEqual(CompteBancaire.objects.count(), 4)


class CompteBancaireAuTests(Base):
    def test_account_in_force_on_a_day(self):
        self.assertIsNone(self.agent.compte_bancaire_au(date(2030, 1, 1)))
        second = self.compte(date(2022, 6, 1), "222222", self.bik)
        first = self.compte(date(2020, 3, 1))
        cases = {
            date(2020, 2, 29): None, date(2020, 3, 1): first, date(2021, 12, 31): first,
            date(2022, 6, 1): second, date(2040, 1, 1): second,
        }  # fmt: skip
        prefetched = Agent.objects.prefetch_related("comptes_bancaires").get(pk=self.agent.pk)
        for jour, expected in cases.items():
            with self.subTest(jour=jour):
                self.assertEqual(self.agent.compte_bancaire_au(jour), expected)
                with self.assertNumQueries(0):
                    self.assertEqual(prefetched.compte_bancaire_au(jour), expected)

    def test_unsaved_agent_has_none(self):
        self.assertIsNone(Agent().compte_bancaire_au(date(2020, 3, 1)))


class CompteBancaireAuditTests(Base):
    def test_create_and_correct_are_audited_under_paie_with_label_and_author(self):
        user = get_user_model().objects.create_user("remuneration", password="x")
        row = CompteBancaire.objects.create(
            agent=self.agent, banque=self.bcf, numero=NUMERO, date_effet=date(2021, 3, 1),
            cree_par=user, modifie_par=user,
        )  # fmt: skip
        row.numero = "05100 0009999"
        row.save()

        entries = EntreeAudit.objects.filter(table__model="comptebancaire", objet_id=row.pk)
        self.assertEqual(
            set(entries.values_list("action", "module", "objet_libelle", "auteur")),
            {
                ("creation", "paie",
                 "BCF — 05100 0001234 depuis le 01/03/2021 — ARPTC/0001/2020", user.pk),
                ("modification", "paie",
                 "BCF — 05100 0009999 depuis le 01/03/2021 — ARPTC/0001/2020", user.pk),
            },
        )  # fmt: skip
