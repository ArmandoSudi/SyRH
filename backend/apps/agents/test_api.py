"""GET /api/agents/ (agent identity D13, D18, D19)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.roles import GROUPS

from .models import Agent

AGENTS = "/api/agents/"
READERS = {name for name, (_, modules) in GROUPS.items() if "agents" in modules}


def member(username, *groups):
    user = get_user_model().objects.create_user(username, password="x")
    user.groups.set(Group.objects.filter(name__in=groups))
    return user


def agent(matricule, nom, **values):
    values = {
        "sexe": "M",
        "date_naissance": date(1985, 3, 14),
        "lieu_naissance": "Kinshasa",
        **values,
    }
    return Agent.objects.create(matricule=matricule, nom=nom, **values)


class AgentApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tshala = agent("C/3", "Tshala", sexe="F", prenom="Marie")
        cls.kabila = agent("B/2", "Kabila", postnom="Mbuyi")
        cls.ilunga = agent("A/1", "Ilunga")
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def client_for(self, user="Auditeur"):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client

    def test_every_profile_opening_agents_reads_them_others_do_not(self):
        self.assertNotIn("Administrateur système", READERS)
        self.assertEqual(self.client_for(None).get(AGENTS).status_code, 401)
        self.assertEqual(self.client_for(self.nobody).get(AGENTS).status_code, 403)
        for name in GROUPS:
            with self.subTest(name):
                expected = 200 if name in READERS else 403
                self.assertEqual(self.client_for(name).get(AGENTS).status_code, expected)

    def test_list_in_name_order_not_paginated(self):
        rows = self.client_for().get(AGENTS).json()
        self.assertEqual(
            [row["id"] for row in rows], [self.ilunga.pk, self.kabila.pk, self.tshala.pk]
        )

    def test_fields(self):
        row = self.client_for().get(f"{AGENTS}{self.tshala.pk}/").json()
        self.assertEqual(
            {k: v for k, v in row.items() if k not in ("date_creation", "date_modification")},
            {
                "id": self.tshala.pk,
                "matricule": "C/3",
                "nom": "Tshala",
                "postnom": "",
                "prenom": "Marie",
                "sexe": "F",
                "sexe_libelle": "Féminin",
                "date_naissance": "1985-03-14",
                "lieu_naissance": "Kinshasa",
                "nationalite": "Congolaise",
                "cree_par": None,
                "modifie_par": None,
            },
        )
        self.assertIn("date_creation", row)
        self.assertIn("date_modification", row)

    def test_unknown_id_is_not_found(self):
        self.assertEqual(self.client_for().get(f"{AGENTS}999999/").status_code, 404)

    def test_nobody_writes_not_even_the_editors(self):
        detail = f"{AGENTS}{self.kabila.pk}/"
        for name in ("Gestion de carrière", "Direction RH"):
            with self.subTest(name):
                client = self.client_for(name)
                self.assertEqual(client.post(AGENTS, {}).status_code, 405)
                self.assertEqual(client.put(detail, {}).status_code, 405)
                self.assertEqual(client.patch(detail, {}).status_code, 405)
                self.assertEqual(client.delete(detail).status_code, 405)
        self.assertEqual(Agent.objects.count(), 3)
