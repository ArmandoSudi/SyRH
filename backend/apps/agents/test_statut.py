"""An agent's computed status. See specs/2026-11-22-agent-list (D1 to D3)."""

from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.referentiels.models import TypeContrat

from .models import Agent, Contrat, StatutAgent
from .test_affectations import D2015, agent

S = StatutAgent


class StatutTests(TestCase):
    """CDD from 01/03/2020 to 28/02/2021, then a CDI from 01/06/2022 (a gap between)."""

    @classmethod
    def setUpTestData(cls):
        cdd = TypeContrat.objects.create(code="CDD", nom="CDD", duree_determinee=True,
                                         periode_essai=True, date_ouverture=D2015)  # fmt: skip
        cls.cdi = TypeContrat.objects.create(code="CDI", nom="CDI", duree_determinee=False,
                                             periode_essai=True, date_ouverture=D2015)  # fmt: skip
        cls.agent = agent()
        Contrat.objects.create(agent=cls.agent, type_contrat=cdd, date_debut=date(2020, 3, 1),
                               date_fin=date(2021, 2, 28))  # fmt: skip
        Contrat.objects.create(agent=cls.agent, type_contrat=cls.cdi, date_debut=date(2022, 6, 1))
        cls.sans = agent("ARPTC/0002/2020", "Sans")

    def both(self, a, jour):
        """The status by the SQL annotation and by the method, which must agree."""
        sql = Agent.objects.with_statut(jour).get(pk=a.pk).statut
        self.assertEqual(sql, a.statut_au(jour), jour)
        return sql

    def test_boundaries(self):
        cases = [
            (date(2020, 2, 29), S.A_VENIR),
            (date(2020, 3, 1), S.ACTIF),
            (date(2021, 2, 28), S.ACTIF),
            (date(2021, 3, 1), S.INACTIF),  # the gap
            (date(2022, 5, 31), S.INACTIF),
            (date(2022, 6, 1), S.ACTIF),
            (date(2030, 1, 1), S.ACTIF),  # open-ended CDI
        ]
        for jour, statut in cases:
            with self.subTest(jour):
                self.assertEqual(self.both(self.agent, jour), statut)

    def test_without_contract(self):
        self.assertEqual(self.both(self.sans, date(2026, 1, 1)), S.SANS_CONTRAT)

    def test_labels_and_order(self):
        self.assertEqual(
            S.choices,
            [("actif", "En activité"), ("a_venir", "À venir"),
             ("inactif", "Sans contrat en cours"), ("sans_contrat", "Sans contrat")],
        )  # fmt: skip

    @override_settings(DEBUG=True)
    def test_annotation_and_method_agree_on_the_demo_agents(self):
        call_command("create_demo_agents", stdout=StringIO())
        days = [date(2015, 1, 1) + timedelta(days=365 * n + 37 * n) for n in range(13)]
        for jour in days:
            annotated = dict(Agent.objects.with_statut(jour).values_list("pk", "statut"))
            for a in Agent.objects.prefetch_related("contrats"):
                self.assertEqual(annotated[a.pk], a.statut_au(jour), (a.matricule, jour))


class StatutMirrorTests(TestCase):
    """The list's status filter reads its own copy of the statuses (agent list D2)."""

    def test_frontend_list_matches_the_backend(self):
        import re
        from pathlib import Path

        from django.conf import settings

        source = (
            Path(settings.BASE_DIR).parent / "frontend/src/features/agents/components/statuts.ts"
        ).read_text()
        pairs = re.findall(r"\{ value: '([a-z_]+)', label: '([^']+)' \}", source)
        self.assertEqual(pairs, [(value, str(label)) for value, label in StatutAgent.choices])
