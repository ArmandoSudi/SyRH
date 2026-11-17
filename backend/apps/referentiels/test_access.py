from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.roles import GROUPS, ORGANISATION_EDIT_PERMISSIONS, sync_groups
from apps.audit.models import EntreeAudit

from .models import Site, UniteOrganisationnelle

T = UniteOrganisationnelle.Type
Unite = UniteOrganisationnelle
EDITORS = {
    "Administrateur système",
    "Gestion de carrière",
    "Chef de service — Gestion de carrière",
}
UNITES = "/api/referentiels/unites/"
SITES = "/api/referentiels/sites/"
D2015 = date(2015, 1, 1)
D2025 = date(2025, 7, 1)


def member(username, *groups, **extra):
    user = get_user_model().objects.create_user(username, password="x", **extra)
    user.groups.set(Group.objects.filter(name__in=groups))
    return user


class PermissionTests(TestCase):
    def holders(self, permission):
        app_label, codename = permission.split(".")
        return set(
            Group.objects.filter(
                permissions__content_type__app_label=app_label, permissions__codename=codename
            ).values_list("name", flat=True)
        )

    def test_editors_hold_view_add_change_on_both_tables(self):
        self.assertEqual(len(ORGANISATION_EDIT_PERMISSIONS), 6)
        for permission in ORGANISATION_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(self.holders(permission), EDITORS)

    def test_nobody_can_delete(self):
        self.assertFalse(
            Permission.objects.filter(
                content_type__app_label="referentiels", codename__startswith="delete_"
            ).exists()
        )

    def test_group_setup_adds_nothing_the_second_time(self):
        before = EntreeAudit.objects.count()
        sync_groups()
        self.assertEqual(EntreeAudit.objects.count(), before)

    @override_settings(DEBUG=True)
    def test_demo_editors_get_staff_status(self):
        call_command("create_demo_users", password="demo-pass-2026", stdout=StringIO())

        staff = set(
            get_user_model()
            .objects.filter(username__startswith="demo.", is_staff=True)
            .values_list("groups__name", flat=True)
        )
        self.assertEqual(staff, EDITORS)
        self.assertTrue(EDITORS <= set(GROUPS))


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.kin = Site.objects.create(code="KIN", nom="Siège", ville="Kinshasa", siege=True)
        cls.drh = Unite.objects.create(
            code="DRH", nom="DRH", type=T.DIRECTION, site=cls.kin, date_ouverture=D2015
        )

    def form(self, **values):
        return {
            "type": T.SERVICE,
            "code": "drh-new",
            "nom": "Service nouveau",
            "parent": self.drh.pk,
            "site": self.kin.pk,
            "date_ouverture": "2020-01-01",
            "date_fermeture": "",
            **values,
        }

    def test_editor_adds_and_changes_a_unit(self):
        self.client.force_login(self.carriere)

        response = self.client.post("/admin/referentiels/uniteorganisationnelle/add/", self.form())
        self.assertEqual(response.status_code, 302)
        unit = Unite.objects.get(code="DRH-NEW")
        self.assertEqual((unit.cree_par, unit.modifie_par), (self.carriere, self.carriere))

        url = f"/admin/referentiels/uniteorganisationnelle/{unit.pk}/change/"
        page = self.client.get(url).content.decode()
        self.assertNotIn('name="parent"', page)  # type, parent and site are read-only (D8)
        self.assertNotIn('name="type"', page)
        self.assertNotIn('name="site"', page)

        response = self.client.post(
            url, {"code": "DRH-NEW", "nom": "Service renommé", "date_ouverture": "2020-01-01"}
        )
        self.assertEqual(response.status_code, 302)
        entry = EntreeAudit.objects.filter(objet_id=unit.pk, action="modification").get()
        self.assertEqual(entry.auteur, self.carriere)

    def test_rule_errors_show_next_to_the_field(self):
        self.client.force_login(self.carriere)
        response = self.client.post(
            "/admin/referentiels/uniteorganisationnelle/add/",
            self.form(date_ouverture="2010-01-01"),
        )

        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("avant son unité parente", errors["date_ouverture"][0])

    def test_editor_cannot_delete(self):
        self.client.force_login(self.carriere)
        url = f"/admin/referentiels/uniteorganisationnelle/{self.drh.pk}/delete/"

        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 403)
        self.assertTrue(Unite.objects.filter(pk=self.drh.pk).exists())

    def test_other_profiles_cannot_open_the_admin_pages(self):
        self.client.force_login(self.remuneration)

        response = self.client.get("/admin/referentiels/uniteorganisationnelle/")
        self.assertEqual(response.status_code, 403)


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.kin = Site.objects.create(code="KIN", nom="Siège", ville="Kinshasa", siege=True)
        cls.old_site = Site.objects.create(
            code="OLD", nom="Ancien", ville="Matadi", date_fermeture=D2025
        )
        cls.dt = Unite.objects.create(
            code="DT", nom="Direction technique", type=T.DIRECTION, site=cls.kin,
            date_ouverture=D2015,
        )  # fmt: skip
        cls.old = Unite.objects.create(
            code="DT-CTL", nom="Service Contrôle", type=T.SERVICE, parent=cls.dt, site=cls.kin,
            date_ouverture=D2015, date_fermeture=D2025,
        )  # fmt: skip
        cls.new = Unite.objects.create(
            code="DT-CTL", nom="Département Contrôle", type=T.DEPARTEMENT, parent=cls.dt,
            site=cls.kin, date_ouverture=D2025,
        )  # fmt: skip
        cls.users = {
            name: member(slug, name) for name, (slug, _) in GROUPS.items()
        }  # every profile opens Référentiels
        cls.nobody = member("personne")

    def get(self, user, url=UNITES, **params):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client.get(url, params)

    def ids(self, response):
        return {row["id"] for row in response.json()}

    def test_access(self):
        self.assertEqual(self.get(None).status_code, 401)
        self.assertEqual(self.get(self.nobody).status_code, 403)
        self.assertEqual(self.get(self.nobody, SITES).status_code, 403)
        for name, user in self.users.items():
            with self.subTest(name):
                self.assertEqual(self.get(user).status_code, 200)
                self.assertEqual(self.get(user, SITES).status_code, 200)

    def test_units_open_today_by_default(self):
        user = self.users["Auditeur"]

        self.assertEqual(self.ids(self.get(user)), {self.dt.pk, self.new.pk})
        past = self.get(user, date="2025-06-30")
        self.assertEqual(self.ids(past), {self.dt.pk, self.old.pk})
        self.assertEqual(
            self.ids(self.get(user, toutes="1")), {self.dt.pk, self.old.pk, self.new.pk}
        )

    def test_unit_fields(self):
        row = next(r for r in self.get(self.users["Auditeur"]).json() if r["id"] == self.new.pk)

        self.assertEqual(
            {k: row[k] for k in ("code", "nom", "type", "type_libelle", "parent", "site")},
            {
                "code": "DT-CTL",
                "nom": "Département Contrôle",
                "type": "departement",
                "type_libelle": "Département",
                "parent": self.dt.pk,
                "site": {"id": self.kin.pk, "code": "KIN", "nom": "Siège"},
            },
        )
        self.assertEqual((row["date_ouverture"], row["date_fermeture"]), ("2025-07-01", None))
        self.assertIn("date_modification", row)

    def test_invalid_date_is_refused_per_field(self):
        response = self.get(self.users["Auditeur"], date="31/12/2025")

        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json())

    def test_sites_open_by_default(self):
        user = self.users["Direction RH"]

        self.assertEqual(self.ids(self.get(user, SITES)), {self.kin.pk})
        self.assertEqual(
            self.ids(self.get(user, SITES, toutes="1")), {self.kin.pk, self.old_site.pk}
        )

    def test_writes_are_refused(self):
        client = APIClient()
        client.force_authenticate(self.users["Gestion de carrière"])
        for url in (UNITES, SITES):
            detail = f"{url}{self.dt.pk if url == UNITES else self.kin.pk}/"
            with self.subTest(url):
                self.assertEqual(client.post(url, {}).status_code, 405)
                self.assertEqual(client.put(detail, {}).status_code, 405)
                self.assertEqual(client.patch(detail, {}).status_code, 405)
                self.assertEqual(client.delete(detail).status_code, 405)

    def test_query_count_does_not_grow_with_units(self):
        user = self.users["Auditeur"]

        def count():
            with CaptureQueriesContext(connection) as queries:
                self.get(user, toutes="1")
            return len(queries)

        count()  # the first request also loads the user's permissions
        before = count()
        for i in range(10):
            Unite.objects.create(
                code=f"S{i}", nom=f"S{i}", type=T.SERVICE, parent=self.dt, site=self.kin,
                date_ouverture=D2015,
            )  # fmt: skip
        self.assertEqual(count(), before)


class DemoOrganisationTests(TestCase):
    def run_command(self):
        call_command("create_demo_organisation", stdout=StringIO())

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(Unite.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_a_valid_tree_once(self):
        self.run_command()

        self.assertEqual(Site.objects.count(), 4)
        self.assertEqual(Site.objects.get(siege=True).code, "KIN")
        for unit in Unite.objects.all():
            unit.full_clean()  # every rule holds
        self.assertEqual(Unite.objects.filter(code="DT-CTL").count(), 2)
        today = timezone.localdate()
        self.assertEqual(
            Unite.objects.ouvertes(today).filter(code="DT-CTL").get().type, "departement"
        )
        self.assertTrue(
            Unite.objects.ouvertes(date(2025, 6, 30)).filter(type="service", code="DT-CTL")
        )
        self.assertTrue(EntreeAudit.objects.filter(module="referentiels", auteur=None).exists())

        counts = (Site.objects.count(), Unite.objects.count(), EntreeAudit.objects.count())
        self.run_command()
        self.assertEqual(
            (Site.objects.count(), Unite.objects.count(), EntreeAudit.objects.count()), counts
        )
