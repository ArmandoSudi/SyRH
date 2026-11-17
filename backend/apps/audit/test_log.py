from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import DatabaseError, connection, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.core.probe import ProbeTestCase

from . import service
from .models import COMPTES, EntreeAudit
from .values import MASK


def make_entry(**overrides):
    values = {
        "action": EntreeAudit.Action.CREATION,
        "table": ContentType.objects.get_for_model(Group),
        "objet_id": 1,
        "objet_libelle": "Social",
        "module": COMPTES,
        "changements": [{"champ": "name", "libelle": "nom", "avant": None, "apres": "Social"}],
    }
    return EntreeAudit.objects.create(**(values | overrides))


class ImmutableLogTests(TestCase):
    def test_entry_is_stored_with_its_changes(self):
        entry = make_entry()

        entry = EntreeAudit.objects.get(pk=entry.pk)
        self.assertEqual(entry.changements[0]["apres"], "Social")
        self.assertIsNotNone(entry.date)

    def test_model_refuses_to_change_an_entry(self):
        entry = make_entry()

        with self.assertRaises(PermissionError):
            entry.save()
        with self.assertRaises(PermissionError):
            entry.delete()
        with self.assertRaises(PermissionError):
            EntreeAudit.objects.filter(pk=entry.pk).update(objet_libelle="x")
        with self.assertRaises(PermissionError):
            EntreeAudit.objects.filter(pk=entry.pk).delete()

    def test_database_refuses_update_and_delete(self):
        entry = make_entry()

        for sql in (
            "UPDATE audit_entreeaudit SET objet_libelle = 'x' WHERE id = %s",
            "DELETE FROM audit_entreeaudit WHERE id = %s",
        ):
            with self.subTest(sql=sql), self.assertRaises(DatabaseError) as raised:
                with transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(sql, [entry.pk])
            self.assertIn("ne peut pas être modifié", str(raised.exception))

        self.assertEqual(EntreeAudit.objects.get(pk=entry.pk).objet_libelle, "Social")

    def test_log_is_not_in_django_admin(self):
        self.assertFalse(admin.site.is_registered(EntreeAudit))


class ProtectedAuthorTests(ProbeTestCase):
    # A ProbeTestCase: deleting a user makes Django check every model that
    # points to users, the test-only Probe included, so its table must exist.
    def test_author_of_an_entry_cannot_be_deleted(self):
        user = get_user_model().objects.create_user("auteur", password="x")
        make_entry(auteur=user)

        with self.assertRaises(ProtectedError):
            user.delete()


class ServiceTests(TestCase):
    """Values and changes, on accounts.User whose fields cover most kinds."""

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()

    def test_changes_between_snapshots(self):
        user = self.User.objects.create_user("mkabila", first_name="Marie")
        before = service.snapshot(user)
        user.first_name = "Mariam"
        user.is_staff = True

        changes = service.changes(self.User, before, service.snapshot(user))

        self.assertEqual(
            changes,
            [
                {"champ": "first_name", "libelle": "prénom", "avant": "Marie", "apres": "Mariam"},
                {"champ": "is_staff", "libelle": "statut équipe", "avant": False, "apres": True},
            ],
        )

    def test_creation_leaves_out_empty_values(self):
        user = self.User(username="nouveau")

        changes = service.changes(self.User, {}, service.snapshot(user))

        fields = [change["champ"] for change in changes]
        self.assertIn("username", fields)
        self.assertNotIn("email", fields)  # empty string
        self.assertTrue(all(change["avant"] is None for change in changes))

    def test_password_is_masked(self):
        user = self.User.objects.create_user("mkabila", password="ancien-mot-de-passe")
        before = service.snapshot(user)
        user.set_password("nouveau-mot-de-passe")

        [change] = service.changes(self.User, before, service.snapshot(user))

        self.assertEqual(
            change, {"champ": "password", "libelle": "mot de passe", "avant": MASK, "apres": MASK}
        )
        self.assertNotIn(user.password, str(change))

    def test_skipped_fields_never_appear(self):
        user = self.User.objects.create_user("mkabila")
        before = service.snapshot(user)

        self.assertNotIn("last_login", before)
        self.assertNotIn("id", before)

    def test_many_to_many_changes_as_labels(self):
        user = self.User.objects.create_user("mkabila")
        social, formation = Group.objects.get(name="Social"), Group.objects.get(name="Formation")
        user.groups.add(social)
        before = service.m2m_snapshot(user, ["groups"])
        user.groups.set([formation])

        changes = service.m2m_changes(self.User, before, service.m2m_snapshot(user, ["groups"]))

        self.assertEqual(
            changes,
            [
                {
                    "champ": "groups",
                    "libelle": "groupes",
                    "ajoutes": ["Formation"],
                    "retires": ["Social"],
                }
            ],
        )

    def test_values_are_json(self):
        from apps.core.probe import Probe

        field = Probe._meta.get_field
        self.assertEqual(service.render(field("montant"), Decimal("12.50")), "12.50")
        self.assertEqual(service.render(field("date_effet"), date(2026, 11, 17)), "2026-11-17")
        user = self.User.objects.create_user("mkabila")
        self.assertEqual(
            service.render(field("responsable"), user.pk), {"id": user.pk, "libelle": "mkabila"}
        )

    def test_modification_without_change_writes_nothing(self):
        user = self.User.objects.create_user("mkabila")

        entry = service.record(user, service.Action.MODIFICATION, [], module=COMPTES)

        self.assertIsNone(entry)
        self.assertFalse(EntreeAudit.objects.filter(objet_id=user.pk, module=COMPTES).exists())
