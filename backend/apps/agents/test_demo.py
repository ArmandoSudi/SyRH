"""create_demo_agents (agent identity D20)."""

from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.audit.models import EntreeAudit

from .models import Agent


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
