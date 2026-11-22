"""Confidential document types and the size limit parameter.
See specs/2026-11-22-document-storage (D12, D13)."""

from datetime import date

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.audit.models import EntreeAudit

from .admin import TypeDocumentForm
from .models import GROUPES_REQUIS, Cle, Parametre, TypeDocument
from .test_edition import EditionTestCase, member

TYPES = "/api/referentiels/types-document/"
D2015 = date(2015, 1, 1)


class ConfidentielModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.social = Group.objects.get(name="Social")
        cls.cmd = TypeDocument.objects.create(
            code="CMD", nom="Certificat médical", date_ouverture=D2015
        )

    def test_not_confidential_by_default(self):
        self.assertFalse(self.cmd.confidentiel)

    def test_confidential_without_group_is_refused(self):
        self.assertEqual(
            TypeDocument.check_groupes(True, []), {"groupes_autorises": [GROUPES_REQUIS]}
        )
        self.assertEqual(TypeDocument.check_groupes(True, [self.social]), {})
        self.assertEqual(TypeDocument.check_groupes(False, []), {})

    def test_set_groupes_is_audited(self):
        auteur = member("chef", "Gestion de carrière")
        self.cmd.set_groupes([self.social], auteur=auteur)
        entry = EntreeAudit.objects.filter(objet_id=self.cmd.pk, action="modification").last()
        self.assertEqual(entry.auteur, auteur)
        self.assertEqual(entry.changements[0]["champ"], "groupes_autorises")
        self.assertEqual(entry.changements[0]["ajoutes"], ["Social"])

    def test_set_same_groupes_writes_nothing(self):
        self.cmd.set_groupes([self.social])
        count = EntreeAudit.objects.count()
        self.cmd.set_groupes([self.social])
        self.assertEqual(EntreeAudit.objects.count(), count)

    def test_lisible_par(self):
        social = member("social", "Social")
        formation = member("formation", "Formation")
        root = member("root")
        root.is_superuser = True
        root.save()
        self.assertTrue(self.cmd.lisible_par(formation))  # not confidential yet
        self.cmd.confidentiel = True
        self.cmd.save()
        self.cmd.set_groupes([self.social])
        self.assertTrue(self.cmd.lisible_par(social))
        self.assertFalse(self.cmd.lisible_par(formation))
        self.assertTrue(self.cmd.lisible_par(root))


class ConfidentielAdminFormTests(TestCase):
    def data(self, **values):
        return {"code": "CMD", "nom": "Certificat médical", "date_ouverture": "2015-01-01",
                **values}  # fmt: skip

    def test_confidential_without_group_shows_on_the_field(self):
        form = TypeDocumentForm(data=self.data(confidentiel="on"))
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["groupes_autorises"], [GROUPES_REQUIS])

    def test_confidential_with_group_is_valid(self):
        social = Group.objects.get(name="Social")
        form = TypeDocumentForm(data=self.data(confidentiel="on", groupes_autorises=[social.pk]))
        self.assertTrue(form.is_valid(), form.errors)


class ConfidentielApiTests(EditionTestCase):
    def setUp(self):
        self.api = self.client_for(self.carriere)
        self.social = Group.objects.get(name="Social")

    def create(self, **values):
        data = {"code": "CMD", "nom": "Certificat médical", "date_ouverture": "2015-01-01",
                **values}  # fmt: skip
        return self.api.post(TYPES, data, format="json")

    def test_list_exposes_the_new_fields(self):
        self.create(confidentiel=True, groupes_autorises=[self.social.pk])
        row = self.api.get(TYPES).json()[0]
        self.assertTrue(row["confidentiel"])
        self.assertEqual(row["groupes_autorises"], [self.social.pk])
        self.assertEqual(row["groupes_autorises_noms"], ["Social"])

    def test_confidential_without_group_is_refused(self):
        response = self.create(confidentiel=True)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["groupes_autorises"], [GROUPES_REQUIS])

    def test_created_with_groups_and_audited_with_its_author(self):
        response = self.create(confidentiel=True, groupes_autorises=[self.social.pk])
        self.assertEqual(response.status_code, 201, response.json())
        row = TypeDocument.objects.get(pk=response.json()["id"])
        self.assertEqual(list(row.groupes_autorises.all()), [self.social])
        entry = EntreeAudit.objects.filter(objet_id=row.pk, action="modification").last()
        self.assertEqual(entry.auteur, self.carriere)

    def test_correcting_the_name_keeps_the_groups(self):
        pk = self.create(confidentiel=True, groupes_autorises=[self.social.pk]).json()["id"]
        response = self.api.patch(f"{TYPES}{pk}/", {"nom": "Certificat"}, format="json")
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["groupes_autorises"], [self.social.pk])

    def test_removing_every_group_of_a_confidential_type_is_refused(self):
        pk = self.create(confidentiel=True, groupes_autorises=[self.social.pk]).json()["id"]
        response = self.api.patch(f"{TYPES}{pk}/", {"groupes_autorises": []}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_successor_carries_the_groups(self):
        pk = self.create(confidentiel=True, groupes_autorises=[self.social.pk]).json()["id"]
        response = self.api.post(
            f"{TYPES}{pk}/successeur/", {"date_effet": "2020-01-01"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.json())
        self.assertTrue(response.json()["confidentiel"])
        self.assertEqual(response.json()["groupes_autorises"], [self.social.pk])


class TailleMaxTests(TestCase):
    def test_bounds(self):
        row = Parametre(cle=Cle.TAILLE_MAX_PIECE, valeur=51, date_ouverture=D2015)
        with self.assertRaises(ValidationError):
            row.full_clean()
        Parametre.objects.create(cle=Cle.TAILLE_MAX_PIECE, valeur=10, date_ouverture=D2015)
        self.assertEqual(Parametre.valeur_au(Cle.TAILLE_MAX_PIECE, date(2026, 1, 1)), 10)


@override_settings(DEBUG=True)
class DemoTests(TestCase):
    def test_demo_types_are_confidential_and_idempotent(self):
        call_command("create_demo_pieces", stdout=open("/dev/null", "w"))
        cmd = TypeDocument.objects.get(code="CMD")
        cni = TypeDocument.objects.get(code="CNI")
        self.assertTrue(cmd.confidentiel and cni.confidentiel)
        self.assertEqual(
            set(cmd.groupes_autorises.values_list("name", flat=True)),
            {"Social", "Chef de service — Social", "Direction RH"},
        )
        self.assertFalse(TypeDocument.objects.get(code="CTR").confidentiel)
        count = EntreeAudit.objects.count()
        call_command("create_demo_pieces", stdout=open("/dev/null", "w"))
        self.assertEqual(EntreeAudit.objects.count(), count)

    def test_demo_size_limit(self):
        call_command("create_demo_parametres", stdout=open("/dev/null", "w"))
        self.assertEqual(Parametre.valeur_au(Cle.TAILLE_MAX_PIECE, date(2026, 1, 1)), 10)
