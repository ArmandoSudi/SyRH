"""create_demo_agents (agent identity D20, contact details D19)."""

from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.audit.models import EntreeAudit

from .models import Agent, Coordonnees


class DemoAgentsTests(TestCase):
    def run_command(self):
        out = StringIO()
        call_command("create_demo_agents", stdout=out)
        return out.getvalue()

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(Agent.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_valid_agents_once(self):
        self.assertIn("12 créés", self.run_command())
        for obj in Agent.objects.all():
            obj.full_clean()  # every rule holds
        self.assertEqual(set(Agent.objects.values_list("sexe", flat=True)), {"M", "F"})
        self.assertTrue(Agent.objects.filter(postnom="").exists())
        self.assertTrue(Agent.objects.exclude(nationalite="Congolaise").exists())
        self.assertFalse(
            EntreeAudit.objects.filter(table__model="agent").exclude(auteur=None).exists()
        )

        before = (Agent.objects.count(), EntreeAudit.objects.count())
        self.assertIn("0 créés", self.run_command())
        self.assertEqual((Agent.objects.count(), EntreeAudit.objects.count()), before)

    @override_settings(DEBUG=True)
    def test_gives_eleven_agents_valid_contact_details_once(self):
        self.assertIn("11 fiches de coordonnées créées", self.run_command())
        rows = Coordonnees.objects.all()
        self.assertEqual(rows.count(), 11)
        for row in rows:
            row.full_clean()  # every rule holds
        self.assertEqual(
            list(
                Agent.objects.filter(coordonnees__isnull=True).values_list("matricule", flat=True)
            ),
            ["ARPTC/0012/2024"],
        )
        for empty in ("courriel", "telephone_secondaire", "urgence_nom"):
            with self.subTest(empty):
                self.assertTrue(rows.filter(**{empty: ""}).exists())
        self.assertTrue(rows.exclude(urgence_nom="").exists())
        self.assertFalse(
            EntreeAudit.objects.filter(table__model="coordonnees").exclude(auteur=None).exists()
        )

        before = (Coordonnees.objects.count(), EntreeAudit.objects.count())
        self.assertIn("0 fiches de coordonnées créées", self.run_command())
        self.assertEqual((Coordonnees.objects.count(), EntreeAudit.objects.count()), before)
