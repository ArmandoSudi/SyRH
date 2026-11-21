"""Who edits agents, and the Django admin (agent identity D14 to D16)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.accounts.roles import AGENT_EDIT_PERMISSIONS, sync_groups
from apps.audit.models import EntreeAudit

from .models import MATRICULE_TAKEN, Agent

EDITORS = {"Gestion de carrière", "Chef de service — Gestion de carrière"}


def member(username, *groups, **extra):
    user = get_user_model().objects.create_user(username, password="x", **extra)
    user.groups.set(Group.objects.filter(name__in=groups))
    return user


def holders(permission):
    app_label, codename = permission.split(".")
    return set(
        Group.objects.filter(
            permissions__content_type__app_label=app_label, permissions__codename=codename
        ).values_list("name", flat=True)
    )


class PermissionTests(TestCase):
    def test_editors_hold_view_add_change(self):
        self.assertEqual(len(AGENT_EDIT_PERMISSIONS), 3)
        for permission in AGENT_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(holders(permission), EDITORS)

    def test_nobody_deletes_and_the_administrator_has_nothing(self):
        self.assertFalse(Permission.objects.filter(codename="delete_agent").exists())
        admin = Group.objects.get(name="Administrateur système")
        self.assertFalse(admin.permissions.filter(content_type__app_label="agents").exists())

    def test_group_setup_regrants_and_keeps_hand_made_ones(self):
        carriere = Group.objects.get(name="Gestion de carrière")
        carriere.permissions.remove(*Permission.objects.filter(codename__endswith="_agent"))
        personnel = Group.objects.get(name="Administration du personnel")
        personnel.permissions.add(Permission.objects.get(codename="view_agent"))

        sync_groups()

        self.assertEqual(holders("agents.change_agent"), EDITORS)
        self.assertEqual(holders("agents.view_agent"), EDITORS | {"Administration du personnel"})


class AgentAdminTests(TestCase):
    AGENTS = "/admin/agents/agent/"

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.chef = member("chef", "Chef de service — Gestion de carrière", is_staff=True)
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.admin = member("admin", "Administrateur système", is_staff=True)
        cls.kabila = Agent.objects.create(
            matricule="ARPTC/0001/2010",
            nom="Kabila",
            sexe="M",
            date_naissance=date(1985, 3, 14),
            lieu_naissance="Kinshasa",
        )

    def setUp(self):
        self.client.force_login(self.carriere)

    def add(self, **values):
        data = {
            "matricule": " arptc/0999/2026 ",
            "nom": "Tshala",
            "postnom": "Mwamba",
            "prenom": "Marie",
            "sexe": "F",
            "date_naissance": "1990-06-01",
            "lieu_naissance": "Lubumbashi",
            "nationalite": "Congolaise",
            **values,
        }
        return self.client.post(f"{self.AGENTS}add/", data)

    def test_list_search_and_filter_open(self):
        for url in (self.AGENTS, f"{self.AGENTS}?q=0001", f"{self.AGENTS}?sexe__exact=F"):
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(f"{self.AGENTS}?q=kabila"), "ARPTC/0001/2010")

    def test_editors_add_an_agent_and_are_its_author(self):
        for user, matricule in ((self.carriere, "A/1"), (self.chef, "A/2")):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.add(matricule=matricule).status_code, 302)
                row = Agent.objects.get(matricule=matricule)
                self.assertEqual(row.cree_par, user)
                entry = EntreeAudit.objects.get(table__model="agent", objet_id=row.pk)
                self.assertEqual(
                    (entry.auteur, entry.module, entry.objet_libelle),
                    (user, "agents", f"{matricule} — Tshala Mwamba Marie"),
                )

    def test_matricule_is_saved_trimmed_in_capitals(self):
        self.add()
        self.assertTrue(Agent.objects.filter(matricule="ARPTC/0999/2026").exists())

    def test_taken_matricule_shows_next_to_the_matricule(self):
        response = self.add(matricule="arptc/0001/2010")
        self.assertEqual(response.status_code, 200)
        form = response.context["adminform"].form
        self.assertEqual(form.errors["matricule"], [MATRICULE_TAKEN])
        self.assertFalse(form.non_field_errors())

    def test_future_birth_shows_next_to_the_date(self):
        response = self.add(date_naissance="2999-01-01")
        self.assertEqual(response.status_code, 200)
        self.assertIn("date_naissance", response.context["adminform"].form.errors)

    def test_matricule_is_read_only_on_change(self):
        url = f"{self.AGENTS}{self.kabila.pk}/change/"
        page = self.client.get(url).content.decode()
        self.assertNotIn('name="matricule"', page)
        self.assertIn('name="nom"', page)
        response = self.client.post(url, {
            "matricule": "X/1", "nom": "Kabila", "postnom": "Mbuyi", "prenom": "",
            "sexe": "M", "date_naissance": "1985-03-14", "lieu_naissance": "Kinshasa",
            "nationalite": "Congolaise"})  # fmt: skip
        self.assertEqual(response.status_code, 302)
        self.kabila.refresh_from_db()
        self.assertEqual((self.kabila.matricule, self.kabila.postnom), ("ARPTC/0001/2010", "Mbuyi"))

    def test_nobody_can_delete_not_even_a_superuser(self):
        superuser = get_user_model().objects.create_superuser("root", password="x")
        for user in (self.carriere, superuser):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                url = f"{self.AGENTS}{self.kabila.pk}/delete/"
                self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 403)
                self.assertNotContains(self.client.get(self.AGENTS), "delete_selected")
        self.assertTrue(Agent.objects.filter(pk=self.kabila.pk).exists())

    def test_other_profiles_cannot_open_the_admin_pages(self):
        for user in (self.remuneration, self.admin):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.AGENTS).status_code, 403)
                self.assertEqual(self.client.get(f"{self.AGENTS}add/").status_code, 403)
