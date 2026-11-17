from decimal import Decimal

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.test import RequestFactory
from django.test.utils import isolate_apps
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.core.checks import module_errors
from apps.core.models import BaseModel, UnauditedWriteError
from apps.core.probe import Probe, ProbeAdmin, ProbeTestCase, ProbeViewSet

from .models import EntreeAudit

Action = EntreeAudit.Action


def entries_for(probe_id):
    return list(
        EntreeAudit.objects.filter(
            table=ContentType.objects.get_for_model(Probe), objet_id=probe_id
        ).order_by("id")
    )


class BaseModelCaptureTests(ProbeTestCase):
    def test_creation_is_logged(self):
        probe = Probe.objects.create(
            nom="Kinshasa", montant=Decimal("10.00"), responsable=self.bruno, cree_par=self.alice
        )

        [entry] = entries_for(probe.pk)
        self.assertEqual(entry.action, Action.CREATION)
        self.assertEqual(entry.auteur, self.alice)
        self.assertEqual(entry.module, "referentiels")
        self.assertEqual(entry.objet_libelle, "Kinshasa")
        self.assertEqual(
            entry.changements,
            [
                {"champ": "nom", "libelle": "nom", "avant": None, "apres": "Kinshasa"},
                {"champ": "montant", "libelle": "montant", "avant": None, "apres": "10.00"},
                {
                    "champ": "responsable",
                    "libelle": "responsable",
                    "avant": None,
                    "apres": {"id": self.bruno.pk, "libelle": "bruno"},
                },
            ],
        )

    def test_modification_logs_old_and_new_values(self):
        probe = Probe.objects.create(nom="Kinshasa", montant=Decimal("10.00"))

        probe.nom = "Goma"
        probe.montant = Decimal("12.50")
        probe.modifie_par = self.bruno
        probe.save()

        entry = entries_for(probe.pk)[-1]
        self.assertEqual(entry.action, Action.MODIFICATION)
        self.assertEqual(entry.auteur, self.bruno)
        self.assertEqual(entry.objet_libelle, "Goma")
        self.assertEqual(
            entry.changements,
            [
                {"champ": "nom", "libelle": "nom", "avant": "Kinshasa", "apres": "Goma"},
                {"champ": "montant", "libelle": "montant", "avant": "10.00", "apres": "12.50"},
            ],
        )

    def test_old_values_come_from_the_database(self):
        probe = Probe.objects.create(nom="Kinshasa")
        stale = Probe.objects.get(pk=probe.pk)
        probe.nom = "Goma"
        probe.save()

        stale.nom = "Matadi"
        stale.save()

        entry = entries_for(probe.pk)[-1]
        self.assertEqual(entry.changements[0]["avant"], "Goma")

    def test_partial_save_logs_only_saved_fields(self):
        probe = Probe.objects.create(nom="Kinshasa", montant=Decimal("10.00"))

        probe.nom = "Goma"
        probe.montant = Decimal("99.00")  # changed in memory, not saved
        probe.save(update_fields=["nom"])

        entry = entries_for(probe.pk)[-1]
        self.assertEqual([change["champ"] for change in entry.changements], ["nom"])

    def test_deletion_logs_old_values(self):
        probe = Probe.objects.create(nom="Kinshasa")
        probe_id = probe.pk

        probe.delete(auteur=self.alice)

        entry = entries_for(probe_id)[-1]
        self.assertEqual(entry.action, Action.SUPPRESSION)
        self.assertEqual(entry.auteur, self.alice)
        self.assertEqual(entry.objet_libelle, "Kinshasa")
        self.assertEqual(
            entry.changements,
            [{"champ": "nom", "libelle": "nom", "avant": "Kinshasa", "apres": None}],
        )

    def test_save_without_change_writes_nothing(self):
        probe = Probe.objects.create(nom="Kinshasa")

        probe.save()

        self.assertEqual(len(entries_for(probe.pk)), 1)

    def test_rolled_back_change_leaves_no_entry(self):
        probe = Probe.objects.create(nom="Kinshasa")

        with self.assertRaises(RuntimeError), transaction.atomic():
            probe.nom = "Goma"
            probe.save()
            raise RuntimeError("rollback")

        self.assertEqual(len(entries_for(probe.pk)), 1)

    def test_system_write_has_no_author(self):
        probe = Probe.objects.create(nom="Import")

        self.assertIsNone(entries_for(probe.pk)[0].auteur)

    def test_unaudited_bulk_writes_are_refused(self):
        Probe.objects.create(nom="Kinshasa")

        with self.assertRaises(UnauditedWriteError):
            Probe.objects.update(nom="Goma")
        with self.assertRaises(UnauditedWriteError):
            Probe.objects.filter(nom="Kinshasa").delete()

    def test_update_audited_logs_each_row(self):
        first = Probe.objects.create(nom="Kinshasa")
        second = Probe.objects.create(nom="Goma")

        count = Probe.objects.all().update_audited(self.bruno, montant=Decimal("5.00"))

        self.assertEqual(count, 2)
        for probe in (first, second):
            entry = entries_for(probe.pk)[-1]
            self.assertEqual(entry.action, Action.MODIFICATION)
            self.assertEqual(entry.auteur, self.bruno)
            probe.refresh_from_db()
            self.assertEqual(probe.modifie_par, self.bruno)


class MixinCaptureTests(ProbeTestCase):
    factory = APIRequestFactory()

    def call(self, action, method, user, data=None, pk=None):
        view = ProbeViewSet.as_view({method: action})
        url = "/probes/" if pk is None else f"/probes/{pk}/"
        request = getattr(self.factory, method)(url, data or {}, format="json")
        force_authenticate(request, user=user)
        return view(request) if pk is None else view(request, pk=pk)

    def test_api_authors_every_entry(self):
        response = self.call("create", "post", self.alice, {"nom": "Kinshasa"})
        probe_id = response.data["id"]
        self.call("partial_update", "patch", self.bruno, {"nom": "Goma"}, pk=probe_id)
        response = self.call("destroy", "delete", self.alice, pk=probe_id)

        self.assertEqual(response.status_code, 204)
        entries = entries_for(probe_id)
        self.assertEqual(
            [(e.action, e.auteur) for e in entries],
            [
                (Action.CREATION, self.alice),
                (Action.MODIFICATION, self.bruno),
                (Action.SUPPRESSION, self.alice),
            ],
        )

    def test_admin_authors_every_entry(self):
        model_admin = ProbeAdmin(Probe, admin.AdminSite())
        request = RequestFactory().post("/admin/core/probe/")
        request.user = self.alice

        probe = Probe(nom="Kinshasa")
        model_admin.save_model(request, probe, form=None, change=False)
        probe_id = probe.pk
        model_admin.delete_queryset(request, Probe.objects.filter(pk=probe_id))

        self.assertEqual(
            [(e.action, e.auteur) for e in entries_for(probe_id)],
            [(Action.CREATION, self.alice), (Action.SUPPRESSION, self.alice)],
        )
        self.assertFalse(Probe.objects.filter(pk=probe_id).exists())


class ModuleCheckTests(ProbeTestCase):
    @isolate_apps("apps.core")
    def test_base_model_must_declare_a_known_module(self):
        class SansModule(BaseModel):
            class Meta:
                app_label = "core"

        class ModuleInconnu(BaseModel):
            module = "compta"

            class Meta:
                app_label = "core"

        class Correct(BaseModel):
            module = "paie"

            class Meta:
                app_label = "core"

        errors = module_errors([SansModule, ModuleInconnu, Correct])

        self.assertEqual([e.obj for e in errors], [SansModule, ModuleInconnu])
        self.assertTrue(all(e.id == "core.E001" for e in errors))

    def test_probe_passes_the_check(self):
        self.assertEqual(module_errors([Probe]), [])
