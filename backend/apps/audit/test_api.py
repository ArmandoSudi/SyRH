from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import COMPTES, EntreeAudit

Action = EntreeAudit.Action
LIST = "/api/audit/entrees/"


class AuditApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        def member(username, group, **extra):
            user = User.objects.create_user(username, password="x", **extra)
            user.groups.add(Group.objects.get(name=group))
            return user

        cls.auditeur = member("auditeur", "Auditeur")
        cls.direction = member("direction", "Direction RH", first_name="Aline", last_name="Mbuyi")
        cls.admin = member("admin.syrh", "Administrateur système")
        cls.carriere = member("carriere", "Gestion de carrière")

        group_type = ContentType.objects.get_for_model(Group)
        cls.entries = {}
        for module in ("paie", "social", "agents", "referentiels", COMPTES):
            cls.entries[module] = EntreeAudit.objects.create(
                auteur=cls.direction,
                action=Action.MODIFICATION,
                table=group_type,
                objet_id=1000,
                objet_libelle=f"Ligne {module}",
                module=module,
                changements=[{"champ": "name", "libelle": "nom", "avant": "a", "apres": "b"}],
            )
        # An older creation, by the system, for the date, author and action filters.
        cls.old = EntreeAudit.objects.create(
            date=timezone.make_aware(datetime(2026, 1, 15, 10, 0)),
            action=Action.CREATION,
            table=group_type,
            objet_id=2000,
            objet_libelle="Ancienne",
            module="agents",
            changements=[],
        )

    def get(self, user, url=LIST, **params):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client.get(url, params)

    def visible_modules(self, user):
        response = self.get(user, objet=1000, table="auth.group")
        self.assertEqual(response.status_code, 200)
        return {row["module"] for row in response.data["results"]}

    def test_anonymous_gets_401(self):
        self.assertEqual(self.get(None).status_code, 401)

    def test_without_access_gets_403(self):
        self.assertEqual(self.get(self.carriere).status_code, 403)

    def test_each_reader_sees_only_their_modules(self):
        self.assertEqual(self.visible_modules(self.auditeur), {"agents", "referentiels", COMPTES})
        self.assertEqual(
            self.visible_modules(self.direction),
            {"paie", "social", "agents", "referentiels", COMPTES},
        )
        self.assertEqual(self.visible_modules(self.admin), {"referentiels", COMPTES})

    def test_hidden_entry_answers_404(self):
        paie = self.entries["paie"]

        self.assertEqual(self.get(self.auditeur, f"{LIST}{paie.pk}/").status_code, 404)
        self.assertEqual(self.get(self.direction, f"{LIST}{paie.pk}/").status_code, 200)

    def test_asking_for_a_hidden_module_returns_nothing(self):
        response = self.get(self.auditeur, module="paie")

        self.assertEqual(response.data["count"], 0)

    def test_detail_returns_changes_and_labels(self):
        entry = self.entries["agents"]

        data = self.get(self.auditeur, f"{LIST}{entry.pk}/").data

        self.assertEqual(data["auteur"], {"id": self.direction.pk, "nom": "Aline Mbuyi"})
        self.assertEqual(data["table"], {"cle": "auth.group", "libelle": "Groupe"})
        self.assertEqual(data["action_libelle"], "Modification")
        self.assertEqual(data["module_libelle"], "Agents")
        self.assertEqual(data["changements"][0]["apres"], "b")

    def test_list_omits_changes_and_shows_system_author(self):
        response = self.get(self.auditeur, objet=2000, table="auth.group")

        [row] = response.data["results"]
        self.assertNotIn("changements", row)
        self.assertEqual(row["auteur"], {"id": None, "nom": "Système"})

    def test_newest_first(self):
        dates = [row["date"] for row in self.get(self.direction).data["results"]]

        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_filters(self):
        today = timezone.localdate()
        cases = {
            "period": ({"date_debut": "2026-01-01", "date_fin": "2026-01-31"}, {"Ancienne"}),
            "author": ({"auteur": "mbuy", "module": "agents"}, {"Ligne agents"}),
            "module": ({"module": "referentiels"}, {"Ligne referentiels"}),
            "action": ({"action": "creation", "table": "auth.group", "objet": 2000}, {"Ancienne"}),
            "combined": (
                {"date_debut": today.isoformat(), "module": "agents", "action": "modification"},
                {"Ligne agents"},
            ),
        }
        for name, (params, expected) in cases.items():
            with self.subTest(name):
                response = self.get(self.direction, **params)
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(
                    {row["objet_libelle"] for row in response.data["results"]}, expected
                )

    def test_invalid_filters_answer_400_per_field(self):
        for params, field in (
            ({"module": "compta"}, "module"),
            ({"action": "validation"}, "action"),
            ({"table": "auth.inconnue"}, "table"),
            ({"objet": 1}, "objet"),
            ({"date_debut": "2026-02-01", "date_fin": "2026-01-01"}, "date_fin"),
        ):
            with self.subTest(field):
                response = self.get(self.direction, **params)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_pages_of_fifty(self):
        group_type = ContentType.objects.get_for_model(Group)
        start = timezone.now() - timedelta(days=30)
        for i in range(60):
            EntreeAudit.objects.create(
                date=start + timedelta(minutes=i),
                action=Action.CREATION,
                table=group_type,
                objet_id=3000 + i,
                objet_libelle=f"Masse {i}",
                module="agents",
            )

        response = self.get(self.direction, module="agents")

        self.assertEqual(len(response.data["results"]), 50)
        self.assertIsNotNone(response.data["next"])

    def test_writes_answer_405(self):
        client = APIClient()
        client.force_authenticate(self.direction)
        entry_url = f"{LIST}{self.entries['agents'].pk}/"

        self.assertEqual(client.post(LIST, {}, format="json").status_code, 405)
        for method in ("put", "patch", "delete"):
            with self.subTest(method):
                self.assertEqual(
                    getattr(client, method)(entry_url, {}, format="json").status_code, 405
                )
