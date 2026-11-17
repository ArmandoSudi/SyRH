from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.test import APIClient

from .models import ModuleAccess
from .permissions import HasModuleAccess
from .roles import ADMIN_GROUP, GROUPS, MODULES, sync_groups


def perms_of(group_name):
    group = Group.objects.get(name=group_name)
    return {f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.all()}


def groups_with(permission):
    app_label, codename = permission.split(".")
    return set(
        Group.objects.filter(
            permissions__content_type__app_label=app_label, permissions__codename=codename
        ).values_list("name", flat=True)
    )


class ModulePermissionTests(TestCase):
    def test_one_french_permission_per_module(self):
        perms = Permission.objects.filter(
            content_type__app_label="accounts", codename__startswith="access_"
        )

        self.assertEqual({p.codename for p in perms}, {f"access_{key}" for key in MODULES})
        self.assertEqual(perms.get(codename="access_paie").name, "Accès au module Paie")

    def test_module_access_has_no_table(self):
        self.assertFalse(ModuleAccess._meta.managed)
        self.assertNotIn(ModuleAccess._meta.db_table, connection.introspection.table_names())


class GroupTests(TestCase):
    MATRIX = {
        "Gestion de carrière": {"agents", "carriere", "referentiels"},
        "Administration du personnel": {"agents", "personnel", "referentiels"},
        "Rémunération": {"agents", "paie", "referentiels"},
        "Social": {"agents", "social", "referentiels"},
        "Formation": {"agents", "formation", "referentiels"},
        "Chef de service — Gestion de carrière": {"agents", "carriere", "referentiels"},
        "Chef de service — Administration du personnel": {"agents", "personnel", "referentiels"},
        "Chef de service — Rémunération": {"agents", "paie", "referentiels"},
        "Chef de service — Social": {"agents", "social", "referentiels"},
        "Chef de service — Formation": {"agents", "formation", "referentiels"},
        "Direction RH": {
            "agents",
            "carriere",
            "personnel",
            "paie",
            "social",
            "formation",
            "referentiels",
            "audit",
        },
        "Auditeur": {"agents", "carriere", "personnel", "formation", "referentiels", "audit"},
        "Administrateur système": {"referentiels", "systeme", "audit"},
    }

    def test_groups_match_the_matrix(self):
        self.assertEqual(set(Group.objects.values_list("name", flat=True)), set(self.MATRIX))
        for name, modules in self.MATRIX.items():
            with self.subTest(name):
                module_perms = {p for p in perms_of(name) if ".access_" in p}
                self.assertEqual(module_perms, {f"accounts.access_{m}" for m in modules})

    def test_salaries_only_for_remuneration_and_direction(self):
        self.assertEqual(
            groups_with("accounts.access_paie"),
            {"Rémunération", "Chef de service — Rémunération", "Direction RH"},
        )

    def test_care_details_only_for_social_and_direction(self):
        self.assertEqual(
            groups_with("accounts.access_social"),
            {"Social", "Chef de service — Social", "Direction RH"},
        )

    def test_auditor_reads_neither_pay_nor_care_details(self):
        perms = perms_of("Auditeur")

        self.assertNotIn("accounts.access_paie", perms)
        self.assertNotIn("accounts.access_social", perms)

    def test_direction_reads_every_hr_module(self):
        hr_modules = set(MODULES) - {"systeme"}

        self.assertEqual(
            {p for p in perms_of("Direction RH") if ".access_" in p},
            {f"accounts.access_{m}" for m in hr_modules},
        )

    def test_system_administrator_manages_accounts_without_deleting(self):
        perms = perms_of(ADMIN_GROUP)

        for name in ("view_user", "add_user", "change_user"):
            self.assertIn(f"accounts.{name}", perms)
        for name in ("view_group", "add_group", "change_group"):
            self.assertIn(f"auth.{name}", perms)
        self.assertNotIn("accounts.delete_user", perms)
        self.assertNotIn("auth.delete_group", perms)
        self.assertNotIn("accounts.access_paie", perms)

    def test_sync_only_adds(self):
        extra = Permission.objects.get(codename="access_formation")
        Group.objects.get(name="Social").permissions.add(extra)

        sync_groups()
        sync_groups()

        self.assertEqual(Group.objects.count(), len(GROUPS))
        self.assertIn("accounts.access_formation", perms_of("Social"))


@api_view(["GET"])
@permission_classes([HasModuleAccess("paie")])
def paie_probe(request):
    return Response({"ok": True})


urlpatterns = [path("probe/paie/", paie_probe)]


@override_settings(ROOT_URLCONF=__name__)
class HasModuleAccessTests(TestCase):
    def user_in(self, *groups):
        user = get_user_model().objects.create_user(f"u{get_user_model().objects.count()}")
        user.groups.set(Group.objects.filter(name__in=groups))
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_anonymous_gets_401(self):
        self.assertEqual(APIClient().get("/probe/paie/").status_code, 401)

    def test_without_the_module_gets_403(self):
        response = self.user_in("Gestion de carrière").get("/probe/paie/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Vous n'avez pas accès à ce module.")

    def test_with_the_module_gets_through(self):
        self.assertEqual(self.user_in("Rémunération").get("/probe/paie/").status_code, 200)

    def test_unknown_module_fails_early(self):
        with self.assertRaises(ValueError):
            HasModuleAccess("compta")


class MePayloadTests(TestCase):
    def test_groups_and_permissions_are_the_union(self):
        user = get_user_model().objects.create_user("double")
        user.groups.set(Group.objects.filter(name__in=["Social", "Formation"]))
        client = APIClient()
        client.force_authenticate(user)

        body = client.get("/api/auth/me/").json()

        self.assertEqual(body["groups"], ["Formation", "Social"])
        self.assertEqual(
            body["permissions"],
            [
                "accounts.access_agents",
                "accounts.access_formation",
                "accounts.access_referentiels",
                "accounts.access_social",
            ],
        )

    def test_user_without_group_has_empty_lists(self):
        client = APIClient()
        client.force_authenticate(get_user_model().objects.create_user("seul"))

        body = client.get("/api/auth/me/").json()

        self.assertEqual((body["groups"], body["permissions"]), ([], []))


class DemoUsersCommandTests(TestCase):
    def run_command(self):
        call_command("create_demo_users", password="demo-pass-2026", stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_creates_one_account_per_group(self):
        self.run_command()

        users = get_user_model().objects.filter(username__startswith="demo.")
        self.assertEqual(users.count(), len(GROUPS))
        for name, (slug, _) in GROUPS.items():
            user = users.get(username=f"demo.{slug}")
            self.assertEqual(list(user.groups.values_list("name", flat=True)), [name])
            self.assertTrue(user.check_password("demo-pass-2026"))
            self.assertFalse(user.is_superuser)
            self.assertEqual(user.is_staff, name == ADMIN_GROUP)

    @override_settings(DEBUG=True)
    def test_rerunning_updates_rather_than_duplicates(self):
        self.run_command()
        self.run_command()

        self.assertEqual(
            get_user_model().objects.filter(username__startswith="demo.").count(), len(GROUPS)
        )

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()

        self.assertFalse(get_user_model().objects.filter(username__startswith="demo.").exists())
