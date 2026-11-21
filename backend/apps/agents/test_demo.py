"""create_demo_agents (agent identity D20, contact details D19, contract D20)."""

from datetime import date
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.audit.models import EntreeAudit

from .models import Agent, Contrat, Coordonnees


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

    @override_settings(DEBUG=True)
    def test_loads_the_types_then_valid_contracts_once(self):
        self.assertIn("16 contrats créés", self.run_command())
        for row in Contrat.objects.select_related("type_contrat"):
            row.full_clean()  # every rule holds, the type open on the start date

        def shape(matricule):
            agent = Agent.objects.get(matricule=matricule)
            return [c.type_contrat.code for c in agent.contrats.order_by("date_debut")]

        self.assertEqual(shape("ARPTC/0006/2014"), ["CDD", "CDD", "CDI"])
        self.assertEqual(shape("ARPTC/0012/2024"), [])
        self.assertTrue(Contrat.objects.exclude(fin_periode_essai=None).exists())

        current = Agent.objects.get(matricule="ARPTC/0011/2022").contrat_au(date(2026, 11, 21))
        self.assertEqual((current.type_contrat.code, current.date_fin), ("CDD", date(2027, 6, 30)))

        hired = {a.matricule: a.date_engagement for a in Agent.objects.all()}
        self.assertEqual(hired["ARPTC/0001/2008"], date(2015, 1, 1))  # demo types open in 2015
        self.assertEqual(hired["ARPTC/0008/2016"], date(2016, 2, 1))
        self.assertIsNone(hired["ARPTC/0012/2024"])
        self.assertFalse(
            EntreeAudit.objects.filter(table__model="contrat").exclude(auteur=None).exists()
        )

        before = (Contrat.objects.count(), EntreeAudit.objects.count())
        self.assertIn("0 contrats créés", self.run_command())
        self.assertEqual((Contrat.objects.count(), EntreeAudit.objects.count()), before)
