"""Agent identity. See specs/2026-11-21-agent-identity."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from apps.audit.models import EntreeAudit

from .models import MATRICULE_FIXED, MATRICULE_TAKEN, Agent

BIRTH = date(1985, 3, 14)


def agent(matricule="ARPTC/0001/2010", nom="Kabila", **values):
    values = {
        "sexe": Agent.Sexe.MASCULIN,
        "date_naissance": BIRTH,
        "lieu_naissance": "Kinshasa",
        **values,
    }
    return Agent.objects.create(matricule=matricule, nom=nom, **values)


def raw(**values):
    """Bypass the model, so only the database decides."""
    values = {
        "matricule": "ARPTC/0001/2010",
        "nom": "Kabila",
        "sexe": "M",
        "date_naissance": BIRTH,
        "lieu_naissance": "Kinshasa",
        **values,
    }
    with transaction.atomic():
        Agent._base_manager.bulk_create([Agent(**values)])


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


def sql(statement, *params):
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(statement, params)


class AgentTests(TestCase):
    def test_agent_is_created_with_its_label(self):
        row = agent(postnom="Mbuyi", prenom="Joseph")
        self.assertEqual(str(row), "ARPTC/0001/2010 — Kabila Mbuyi Joseph")
        self.assertEqual(str(agent("ARPTC/0002/2010", "Tshala")), "ARPTC/0002/2010 — Tshala")

    def test_required_fields(self):
        self.assertEqual(
            set(errors_of(Agent(nationalite="").full_clean)),
            {"matricule", "nom", "sexe", "date_naissance", "lieu_naissance", "nationalite"},
        )

    def test_postnom_and_prenom_are_optional_and_nationality_has_a_default(self):
        row = Agent(
            matricule="A1", nom="Ilunga", sexe="F", date_naissance=BIRTH, lieu_naissance="Goma"
        )
        row.full_clean()
        self.assertEqual(row.nationalite, "Congolaise")

    def test_matricule_and_names_are_normalised(self):
        row = agent(" arptc/12/2010 ", "  Kabila ", postnom=" Mbuyi ", prenom=" Joseph ")
        row.refresh_from_db()
        self.assertEqual(
            (row.matricule, row.nom, row.postnom, row.prenom),
            ("ARPTC/12/2010", "Kabila", "Mbuyi", "Joseph"),
        )

    def test_bad_matricule_is_reported_on_its_field(self):
        for matricule in ("ARPTC 12", "ARPTC#12", "A" * 21):
            with self.subTest(matricule=matricule):
                row = Agent(
                    matricule=matricule,
                    nom="Kabila",
                    sexe="M",
                    date_naissance=BIRTH,
                    lieu_naissance="Kinshasa",
                )
                errors = errors_of(row.full_clean)
                self.assertIn("matricule", errors)
                self.assertNotIn("__all__", errors)
        with self.assertRaises(ValidationError):
            agent("ARPTC 12")

    def test_taken_matricule_in_another_case_is_reported_on_its_field(self):
        agent("ARPTC/0001/2010")
        row = Agent(
            matricule="arptc/0001/2010",
            nom="Tshala",
            sexe="F",
            date_naissance=BIRTH,
            lieu_naissance="Kinshasa",
        )
        self.assertEqual(errors_of(row.full_clean), {"matricule": [MATRICULE_TAKEN]})
        with self.assertRaises(ValidationError):
            row.save()

    def test_matricule_cannot_change_but_names_can(self):
        row = agent()
        row.postnom = "Mbuyi"
        row.full_clean()
        row.save()

        row.matricule = "ARPTC/0002/2010"
        self.assertEqual(errors_of(row.full_clean), {"matricule": [MATRICULE_FIXED]})
        with self.assertRaises(ValidationError):
            row.save()
        row.refresh_from_db()
        self.assertEqual(row.matricule, "ARPTC/0001/2010")

    def test_future_birth_is_reported_on_its_field(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        row = Agent(
            matricule="A1", nom="Kabila", sexe="M", date_naissance=tomorrow, lieu_naissance="Goma"
        )
        self.assertIn("date_naissance", errors_of(row.full_clean))
        with self.assertRaises(ValidationError):
            row.save()
        row.date_naissance = timezone.localdate()
        row.full_clean()

    def test_ordered_by_names_then_matricule(self):
        agent("C3", "Tshala")
        agent("B2", "Kabila", postnom="Mbuyi")
        agent("A1", "Kabila", postnom="Mbuyi")
        agent("D4", "Kabila")
        self.assertEqual(
            list(Agent.objects.values_list("matricule", flat=True)), ["D4", "A1", "B2", "C3"]
        )

    def test_never_deleted(self):
        row = agent()
        with self.assertRaises(PermissionError):
            row.delete()
        self.assertTrue(Agent.objects.filter(pk=row.pk).exists())
        self.assertEqual(Agent._meta.default_permissions, ("view", "add", "change"))


class AgentConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D8, D11)."""

    def test_valid_row_is_accepted(self):
        raw()
        self.assertEqual(Agent.objects.count(), 1)

    def test_duplicate_matricule_in_another_case_is_refused(self):
        raw(matricule="ARPTC/1")
        with self.assertRaises(IntegrityError):
            raw(matricule="arptc/1")

    def test_bad_matricule_is_refused(self):
        for matricule in ("arptc/1", "ARPTC 1", "ARPTC#1", ""):
            with self.subTest(matricule=matricule), self.assertRaises(IntegrityError):
                raw(matricule=matricule)

    def test_blank_nom_is_refused(self):
        for nom in ("", "   "):
            with self.subTest(nom=nom), self.assertRaises(IntegrityError):
                raw(nom=nom)

    def test_unknown_sexe_is_refused(self):
        with self.assertRaises(IntegrityError):
            raw(sexe="X")

    def test_birth_before_1900_is_refused(self):
        with self.assertRaises(IntegrityError):
            raw(date_naissance=date(1899, 12, 31))
        raw(date_naissance=date(1900, 1, 1))


class AgentTriggerTests(TestCase):
    """The matricule is fixed and an agent never deleted, even in raw SQL (D9, D10)."""

    def setUp(self):
        self.row = agent()

    def test_matricule_update_is_refused(self):
        with self.assertRaises(IntegrityError):
            sql("UPDATE agents_agent SET matricule = 'X' WHERE id = %s", self.row.pk)
        self.row.refresh_from_db()
        self.assertEqual(self.row.matricule, "ARPTC/0001/2010")

    def test_name_update_is_accepted(self):
        sql("UPDATE agents_agent SET postnom = 'Mbuyi' WHERE id = %s", self.row.pk)
        self.row.refresh_from_db()
        self.assertEqual(self.row.postnom, "Mbuyi")

    def test_delete_is_refused(self):
        with self.assertRaises(IntegrityError):
            sql("DELETE FROM agents_agent WHERE id = %s", self.row.pk)
        self.assertTrue(Agent.objects.filter(pk=self.row.pk).exists())


class AgentAuditTests(TestCase):
    def test_create_and_change_are_audited_with_label_and_author(self):
        user = get_user_model().objects.create_user("carriere", password="x")
        row = agent(cree_par=user)
        row.postnom = "Mbuyi"
        row.modifie_par = user
        row.save()

        entries = EntreeAudit.objects.filter(table__model="agent", objet_id=row.pk)
        self.assertEqual(
            set(entries.values_list("action", "module", "objet_libelle", "auteur")),
            {
                ("creation", "agents", "ARPTC/0001/2010 — Kabila", user.pk),
                ("modification", "agents", "ARPTC/0001/2010 — Kabila Mbuyi", user.pk),
            },
        )
