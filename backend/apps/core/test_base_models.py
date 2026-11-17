from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import connection, models
from django.db.migrations.loader import MigrationLoader
from django.db.models import ProtectedError
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.test import APIRequestFactory, force_authenticate

from .admin import BaseModelAdmin
from .mixins import AuthorMixin
from .models import BASE_FIELDS, BaseModel
from .serializers import BaseModelSerializer


class Probe(BaseModel):
    """Test-only concrete model: no migration, table created by the tests."""

    nom = models.CharField(max_length=50)

    class Meta:
        app_label = "core"
        managed = False
        db_table = "core_test_probe"

    def __str__(self):
        return self.nom


class ProbeSerializer(BaseModelSerializer):
    class Meta:
        model = Probe
        fields = ["id", "nom", *BASE_FIELDS]


class ProbeViewSet(AuthorMixin, viewsets.ModelViewSet):
    queryset = Probe.objects.all()
    serializer_class = ProbeSerializer


class ProbeAdmin(BaseModelAdmin, admin.ModelAdmin):
    readonly_fields = ["nom"]


class ProbeTestCase(TestCase):
    """Creates the Probe table inside the class transaction, rolled back after."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            editor.create_model(Probe)

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice = User.objects.create_user("alice", password="x")
        cls.bruno = User.objects.create_user("bruno", password="x")

    def make_old(self, probe):
        """Push date_modification into the past, so a later save visibly moves it."""
        old = timezone.now() - timedelta(days=1)
        Probe.objects.filter(pk=probe.pk).update(date_modification=old)
        probe.refresh_from_db()
        return old


class BaseModelTests(ProbeTestCase):
    def test_base_is_abstract_with_french_fields(self):
        self.assertTrue(BaseModel._meta.abstract)
        labels = {name: Probe._meta.get_field(name).verbose_name for name in BASE_FIELDS}
        self.assertEqual(
            labels,
            {
                "date_creation": "date de création",
                "date_modification": "date de modification",
                "cree_par": "créé par",
                "modifie_par": "modifié par",
            },
        )

    def test_create_sets_both_dates(self):
        probe = Probe.objects.create(nom="Kinshasa")

        self.assertTrue(timezone.is_aware(probe.date_creation))
        self.assertTrue(timezone.is_aware(probe.date_modification))
        self.assertLess(probe.date_modification - probe.date_creation, timedelta(seconds=1))

    def test_save_moves_modification_date_only(self):
        probe = Probe.objects.create(nom="Kinshasa")
        created = probe.date_creation
        old = self.make_old(probe)

        probe.nom = "Lubumbashi"
        probe.save()
        probe.refresh_from_db()

        self.assertGreater(probe.date_modification, old)
        self.assertEqual(probe.date_creation, created)

    def test_partial_save_still_stamps_modification(self):
        probe = Probe.objects.create(nom="Kinshasa")
        old = self.make_old(probe)

        probe.nom = "Matadi"
        probe.modifie_par = self.bruno
        probe.save(update_fields=["nom"])
        probe.refresh_from_db()

        self.assertGreater(probe.date_modification, old)
        self.assertEqual(probe.modifie_par, self.bruno)

    def test_authors_may_be_empty(self):
        probe = Probe.objects.create(nom="Import")

        self.assertIsNone(probe.cree_par)
        self.assertIsNone(probe.modifie_par)

    def test_author_cannot_be_deleted(self):
        Probe.objects.create(nom="Kinshasa", cree_par=self.alice)
        Probe.objects.create(nom="Goma", modifie_par=self.bruno)

        with self.assertRaises(ProtectedError):
            self.alice.delete()
        with self.assertRaises(ProtectedError):
            self.bruno.delete()

    def test_user_gains_no_reverse_accessor(self):
        relations = [
            rel
            for rel in get_user_model()._meta.get_fields(include_hidden=True)
            if rel.is_relation and rel.auto_created and rel.related_model is Probe
        ]

        self.assertEqual(len(relations), 2)
        self.assertTrue(all(rel.hidden for rel in relations))

    def test_probe_is_in_no_migration(self):
        state = MigrationLoader(connection, ignore_no_migrations=True).project_state()

        self.assertNotIn(("core", "probe"), state.models)
        self.assertEqual([m for (app, m) in state.models if app == "core"], [])


class AuthorMixinTests(ProbeTestCase):
    factory = APIRequestFactory()

    def call(self, action, method, user=None, data=None, pk=None):
        view = ProbeViewSet.as_view({method: action})
        url = "/probes/" if pk is None else f"/probes/{pk}/"
        request = getattr(self.factory, method)(url, data or {}, format="json")
        if user is not None:
            force_authenticate(request, user=user)
        return view(request) if pk is None else view(request, pk=pk)

    def test_create_stamps_both_authors(self):
        response = self.call("create", "post", self.alice, {"nom": "Kinshasa"})

        self.assertEqual(response.status_code, 201)
        probe = Probe.objects.get()
        self.assertEqual(probe.cree_par, self.alice)
        self.assertEqual(probe.modifie_par, self.alice)

    def test_update_by_another_user_keeps_creator(self):
        probe = Probe.objects.create(nom="Kinshasa", cree_par=self.alice, modifie_par=self.alice)
        created = probe.date_creation
        old = self.make_old(probe)

        response = self.call("update", "put", self.bruno, {"nom": "Goma"}, pk=probe.pk)

        self.assertEqual(response.status_code, 200)
        probe.refresh_from_db()
        self.assertEqual(probe.cree_par, self.alice)
        self.assertEqual(probe.modifie_par, self.bruno)
        self.assertEqual(probe.date_creation, created)
        self.assertGreater(probe.date_modification, old)

    def test_partial_update_stamps_modification(self):
        probe = Probe.objects.create(nom="Kinshasa", cree_par=self.alice, modifie_par=self.alice)
        old = self.make_old(probe)

        response = self.call("partial_update", "patch", self.bruno, {"nom": "Bukavu"}, pk=probe.pk)

        self.assertEqual(response.status_code, 200)
        probe.refresh_from_db()
        self.assertEqual(probe.modifie_par, self.bruno)
        self.assertGreater(probe.date_modification, old)

    def test_client_values_for_base_fields_are_ignored(self):
        forged = {
            "date_creation": "2000-01-01T00:00:00Z",
            "date_modification": "2000-01-01T00:00:00Z",
            "cree_par": self.bruno.pk,
            "modifie_par": self.bruno.pk,
        }

        self.call("create", "post", self.alice, {"nom": "Kinshasa", **forged})
        probe = Probe.objects.get()
        self.assertEqual(probe.cree_par, self.alice)
        self.assertEqual(probe.modifie_par, self.alice)
        self.assertGreater(probe.date_creation.year, 2000)

        data = {"nom": "Kisangani", **forged}
        self.call("partial_update", "patch", self.alice, data, pk=probe.pk)
        probe.refresh_from_db()
        self.assertEqual(probe.nom, "Kisangani")
        self.assertEqual(probe.cree_par, self.alice)
        self.assertEqual(probe.modifie_par, self.alice)
        self.assertGreater(probe.date_modification.year, 2000)

    def test_response_includes_base_fields_with_author_ids(self):
        response = self.call("create", "post", self.alice, {"nom": "Kinshasa"})

        for name in BASE_FIELDS:
            self.assertIn(name, response.data)
        self.assertEqual(response.data["cree_par"], self.alice.pk)
        self.assertEqual(response.data["modifie_par"], self.alice.pk)

    def test_anonymous_write_is_refused(self):
        response = self.call("create", "post", data={"nom": "Kinshasa"})

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Probe.objects.exists())


class BaseModelAdminTests(ProbeTestCase):
    def setUp(self):
        self.model_admin = ProbeAdmin(Probe, admin.AdminSite())

    def request_by(self, user):
        request = RequestFactory().post("/admin/core/probe/")
        request.user = user
        return request

    def test_add_stamps_both_authors(self):
        probe = Probe(nom="Kinshasa")

        self.model_admin.save_model(self.request_by(self.alice), probe, form=None, change=False)

        probe.refresh_from_db()
        self.assertEqual(probe.cree_par, self.alice)
        self.assertEqual(probe.modifie_par, self.alice)

    def test_change_stamps_modifier_only(self):
        probe = Probe.objects.create(nom="Kinshasa", cree_par=self.alice, modifie_par=self.alice)

        probe.nom = "Goma"
        self.model_admin.save_model(self.request_by(self.bruno), probe, form=None, change=True)

        probe.refresh_from_db()
        self.assertEqual(probe.cree_par, self.alice)
        self.assertEqual(probe.modifie_par, self.bruno)

    def test_base_fields_are_read_only_with_own_fields(self):
        fields = self.model_admin.get_readonly_fields(self.request_by(self.alice))

        self.assertEqual(tuple(fields), ("nom", *BASE_FIELDS))
