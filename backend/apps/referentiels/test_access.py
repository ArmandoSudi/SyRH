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

from apps.accounts.roles import (
    BANQUE_EDIT_PERMISSIONS,
    CLASSIFICATION_EDIT_PERMISSIONS,
    DOCUMENT_EDIT_PERMISSIONS,
    FONCTION_EDIT_PERMISSIONS,
    GROUPS,
    ORGANISATION_EDIT_PERMISSIONS,
    PARAMETRE_EDIT_PERMISSIONS,
    SORTIE_EDIT_PERMISSIONS,
    TYPE_CONTRAT_EDIT_PERMISSIONS,
    sync_groups,
)
from apps.audit.models import EntreeAudit

from .models import (
    Banque,
    Categorie,
    Echelon,
    Fonction,
    Grade,
    MotifSortie,
    Parametre,
    PieceRequise,
    Site,
    TypeContrat,
    TypeDocument,
    TypeSuspension,
    UniteOrganisationnelle,
)

T = UniteOrganisationnelle.Type
Unite = UniteOrganisationnelle
EDITORS = {
    "Administrateur système",
    "Gestion de carrière",
    "Chef de service — Gestion de carrière",
}
# Banks belong to pay: Rémunération edits them instead of Gestion de carrière (banks D12).
BANK_EDITORS = {"Administrateur système", "Rémunération", "Chef de service — Rémunération"}
UNITES = "/api/referentiels/unites/"
SITES = "/api/referentiels/sites/"
CATEGORIES = "/api/referentiels/categories/"
GRADES = "/api/referentiels/grades/"
ECHELONS = "/api/referentiels/echelons/"
CLASSIFICATION = (CATEGORIES, GRADES, ECHELONS)
FONCTIONS = "/api/referentiels/fonctions/"
TYPES_CONTRAT = "/api/referentiels/types-contrat/"
TYPES_DOCUMENT = "/api/referentiels/types-document/"
PIECES = "/api/referentiels/pieces-requises/"
MOTIFS = "/api/referentiels/motifs-sortie/"
SUSPENSIONS = "/api/referentiels/types-suspension/"
BANQUES = "/api/referentiels/banques/"
D2020 = date(2020, 1, 1)
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

    def test_editors_hold_view_add_change_on_the_classification(self):
        self.assertEqual(len(CLASSIFICATION_EDIT_PERMISSIONS), 9)
        for permission in CLASSIFICATION_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(self.holders(permission), EDITORS)

    def test_group_setup_grants_missing_classification_permissions(self):
        group = Group.objects.get(name="Gestion de carrière")
        group.permissions.remove(*Permission.objects.filter(codename__endswith="_grade"))

        sync_groups()

        self.assertEqual(self.holders("referentiels.change_grade"), EDITORS)

    def test_editors_hold_view_add_change_on_fonctions(self):
        self.assertEqual(len(FONCTION_EDIT_PERMISSIONS), 3)
        for permission in FONCTION_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(self.holders(permission), EDITORS)

    def test_group_setup_regrants_fonction_permissions_and_keeps_hand_made_ones(self):
        carriere = Group.objects.get(name="Gestion de carrière")
        carriere.permissions.remove(*Permission.objects.filter(codename__endswith="_fonction"))
        social = Group.objects.get(name="Social")
        social.permissions.add(Permission.objects.get(codename="view_fonction"))

        sync_groups()

        self.assertEqual(self.holders("referentiels.change_fonction"), EDITORS)
        self.assertEqual(self.holders("referentiels.view_fonction"), EDITORS | {"Social"})

    def test_editors_hold_view_add_change_on_contract_types(self):
        self.assertEqual(len(TYPE_CONTRAT_EDIT_PERMISSIONS), 3)
        for permission in TYPE_CONTRAT_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(self.holders(permission), EDITORS)

    def test_group_setup_regrants_contract_type_permissions_and_keeps_hand_made_ones(self):
        carriere = Group.objects.get(name="Gestion de carrière")
        carriere.permissions.remove(*Permission.objects.filter(codename__endswith="_typecontrat"))
        social = Group.objects.get(name="Social")
        social.permissions.add(Permission.objects.get(codename="view_typecontrat"))

        sync_groups()

        self.assertEqual(self.holders("referentiels.change_typecontrat"), EDITORS)
        self.assertEqual(self.holders("referentiels.view_typecontrat"), EDITORS | {"Social"})

    def test_editors_hold_view_add_change_on_documents(self):
        self.assertEqual(len(DOCUMENT_EDIT_PERMISSIONS), 6)
        for permission in DOCUMENT_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(self.holders(permission), EDITORS)

    def test_group_setup_regrants_document_permissions_and_keeps_hand_made_ones(self):
        carriere = Group.objects.get(name="Gestion de carrière")
        carriere.permissions.remove(*Permission.objects.filter(codename__endswith="_piecerequise"))
        personnel = Group.objects.get(name="Administration du personnel")
        personnel.permissions.add(Permission.objects.get(codename="change_piecerequise"))

        sync_groups()

        self.assertEqual(self.holders("referentiels.view_piecerequise"), EDITORS)
        self.assertEqual(
            self.holders("referentiels.change_piecerequise"),
            EDITORS | {"Administration du personnel"},
        )

    def test_editors_hold_view_add_change_on_exit_and_suspension_reasons(self):
        self.assertEqual(len(SORTIE_EDIT_PERMISSIONS), 6)
        for permission in SORTIE_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(self.holders(permission), EDITORS)

    def test_group_setup_regrants_sortie_permissions_and_keeps_hand_made_ones(self):
        carriere = Group.objects.get(name="Gestion de carrière")
        carriere.permissions.remove(*Permission.objects.filter(codename__endswith="_motifsortie"))
        social = Group.objects.get(name="Social")
        social.permissions.add(Permission.objects.get(codename="view_typesuspension"))

        sync_groups()

        self.assertEqual(self.holders("referentiels.change_motifsortie"), EDITORS)
        self.assertEqual(self.holders("referentiels.view_typesuspension"), EDITORS | {"Social"})

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
        self.assertEqual(staff, EDITORS | BANK_EDITORS)
        self.assertTrue(EDITORS | BANK_EDITORS <= set(GROUPS))

    def test_editors_hold_view_add_change_on_parameters(self):
        self.assertEqual(len(PARAMETRE_EDIT_PERMISSIONS), 3)
        for permission in PARAMETRE_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(self.holders(permission), EDITORS)

    def test_group_setup_regrants_parameter_permissions_and_keeps_hand_made_ones(self):
        carriere = Group.objects.get(name="Gestion de carrière")
        carriere.permissions.remove(*Permission.objects.filter(codename__endswith="_parametre"))
        personnel = Group.objects.get(name="Administration du personnel")
        personnel.permissions.add(Permission.objects.get(codename="view_parametre"))

        sync_groups()

        self.assertEqual(self.holders("referentiels.change_parametre"), EDITORS)
        self.assertEqual(
            self.holders("referentiels.view_parametre"),
            EDITORS | {"Administration du personnel"},
        )

    def test_bank_editors_hold_view_add_change_and_nobody_else_edits(self):
        self.assertEqual(len(BANQUE_EDIT_PERMISSIONS), 3)
        self.assertEqual(self.holders("referentiels.view_banque"), BANK_EDITORS)
        self.assertEqual(self.holders("referentiels.add_banque"), BANK_EDITORS)
        self.assertEqual(self.holders("referentiels.change_banque"), BANK_EDITORS)
        self.assertNotIn("Gestion de carrière", self.holders("referentiels.change_banque"))

    def test_remuneration_edits_no_other_reference_table(self):
        remuneration = Group.objects.get(name="Rémunération")
        codenames = set(
            remuneration.permissions.filter(content_type__app_label="referentiels").values_list(
                "codename", flat=True
            )
        )
        self.assertEqual(codenames, {"view_banque", "add_banque", "change_banque"})
        self.assertEqual(self.holders("referentiels.change_fonction"), EDITORS)

    def test_group_setup_regrants_bank_permissions_and_keeps_hand_made_ones(self):
        chef = Group.objects.get(name="Chef de service — Rémunération")
        chef.permissions.remove(*Permission.objects.filter(codename__endswith="_banque"))
        carriere = Group.objects.get(name="Gestion de carrière")
        carriere.permissions.add(Permission.objects.get(codename="view_banque"))

        sync_groups()

        self.assertEqual(self.holders("referentiels.change_banque"), BANK_EDITORS)
        self.assertEqual(
            self.holders("referentiels.view_banque"), BANK_EDITORS | {"Gestion de carrière"}
        )


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


class ClassificationAdminTests(TestCase):
    """Catégories, grades and échelons in Django admin (classification D18, D21, D22)."""

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.cd = Categorie.objects.create(code="CD", nom="Cadres", rang=4, date_ouverture=D2015)
        cls.am = Categorie.objects.create(code="AM", nom="Maîtrise", rang=2, date_ouverture=D2015)
        cls.a1 = Grade.objects.create(
            code="A1", nom="Attaché", categorie=cls.cd, rang=1, date_ouverture=D2015
        )

    def setUp(self):
        self.client.force_login(self.carriere)

    def url(self, model, obj=None, action="add"):
        base = f"/admin/referentiels/{model}/"
        return f"{base}add/" if obj is None else f"{base}{obj.pk}/{action}/"

    def test_editor_adds_a_grade_and_its_echelons(self):
        response = self.client.post(
            self.url("grade"),
            {"categorie": self.cd.pk, "code": "a2", "nom": "Attaché 2", "rang": 2,
             "date_ouverture": "2020-01-01", "date_fermeture": ""},
        )  # fmt: skip
        self.assertEqual(response.status_code, 302)
        a2 = Grade.objects.get(code="A2")
        self.assertEqual((a2.cree_par, a2.modifie_par), (self.carriere, self.carriere))

        for numero in (1, 2, 4):  # a gap is accepted (D5)
            response = self.client.post(
                self.url("echelon"),
                {"grade": a2.pk, "numero": numero, "date_ouverture": "2020-01-01",
                 "date_fermeture": ""},
            )  # fmt: skip
            self.assertEqual(response.status_code, 302)
        self.assertEqual(list(a2.echelons.values_list("numero", flat=True)), [1, 2, 4])
        entry = EntreeAudit.objects.get(table__model="echelon", objet_libelle="A2 — Échelon 4")
        self.assertEqual(entry.auteur, self.carriere)

    def test_add_pages_and_parent_autocomplete_open(self):
        for model in ("categorie", "grade", "echelon"):
            with self.subTest(model):
                self.assertEqual(self.client.get(self.url(model)).status_code, 200)

        for model, field, code in (("grade", "categorie", "CD"), ("echelon", "grade", "A1")):
            with self.subTest(field):
                response = self.client.get(
                    "/admin/autocomplete/",
                    {"app_label": "referentiels", "model_name": model, "field_name": field,
                     "term": code},
                )  # fmt: skip
                self.assertEqual(response.status_code, 200)
                self.assertIn(code, [r["text"][:2] for r in response.json()["results"]])

    def test_editor_corrects_a_grade_but_not_its_categorie(self):
        url = self.url("grade", self.a1, "change")
        page = self.client.get(url).content.decode()
        self.assertNotIn('name="categorie"', page)  # read-only (D11)

        response = self.client.post(
            url, {"code": "A1", "nom": "Attaché corrigé", "rang": 1, "date_ouverture": "2015-01-01"}
        )
        self.assertEqual(response.status_code, 302)
        self.a1.refresh_from_db()
        self.assertEqual((self.a1.nom, self.a1.categorie), ("Attaché corrigé", self.cd))
        entry = EntreeAudit.objects.get(objet_id=self.a1.pk, action="modification")
        self.assertEqual(entry.auteur, self.carriere)

    def test_echelon_grade_is_read_only_on_change(self):
        step = Echelon.objects.create(grade=self.a1, numero=1, date_ouverture=D2015)
        page = self.client.get(self.url("echelon", step, "change")).content.decode()
        self.assertNotIn('name="grade"', page)
        self.assertIn('name="numero"', page)

    def test_rule_errors_show_next_to_the_field(self):
        response = self.client.post(
            self.url("echelon"),
            {"grade": self.a1.pk, "numero": 1, "date_ouverture": "2010-01-01",
             "date_fermeture": ""},
        )  # fmt: skip

        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("ne peut pas ouvrir avant son grade", errors["date_ouverture"][0])

    def test_constraint_errors_show_at_the_top(self):
        response = self.client.post(
            self.url("grade"),
            {"categorie": self.am.pk, "code": "a1", "nom": "Doublon", "rang": 1,
             "date_ouverture": "2020-01-01", "date_fermeture": ""},
        )  # fmt: skip

        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.non_field_errors()
        self.assertIn("Un autre grade porte déjà ce code", errors[0])

    def test_editor_cannot_delete(self):
        for model, obj in (("categorie", self.cd), ("grade", self.a1)):
            with self.subTest(model):
                response = self.client.post(self.url(model, obj, "delete"), {"post": "yes"})
                self.assertEqual(response.status_code, 403)
                self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())

    def test_other_profiles_cannot_open_the_admin_pages(self):
        self.client.force_login(self.remuneration)
        for model in ("categorie", "grade", "echelon"):
            with self.subTest(model):
                response = self.client.get(f"/admin/referentiels/{model}/")
                self.assertEqual(response.status_code, 403)


class FonctionAdminTests(TestCase):
    """Fonctions in Django admin (fonctions D11, D13)."""

    URL = "/admin/referentiels/fonction/"

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.jur = Fonction.objects.create(
            code="JUR", nom="Juriste", nature="execution", date_ouverture=D2015
        )

    def setUp(self):
        self.client.force_login(self.carriere)

    def post(self, url, **values):
        data = {"code": "", "nom": "", "nature": "execution", "date_ouverture": "2020-01-01",
                "date_fermeture": "", **values}  # fmt: skip
        return self.client.post(url, data)

    def test_list_filters_and_search_open(self):
        for query in ("", "?nature__exact=responsabilite", "?statut=ouvert", "?q=jur"):
            with self.subTest(query):
                response = self.client.get(self.URL + query)
                self.assertEqual(response.status_code, 200)
        self.assertContains(self.client.get(self.URL + "?q=jurist"), "Juriste")

    def test_editor_adds_and_corrects_a_fonction(self):
        response = self.post(f"{self.URL}add/", code="cs", nom="Chef de servce",
                             nature="responsabilite")  # fmt: skip
        self.assertEqual(response.status_code, 302)
        cs = Fonction.objects.get(code="CS")
        self.assertEqual((cs.cree_par, cs.modifie_par), (self.carriere, self.carriere))

        response = self.post(f"{self.URL}{cs.pk}/change/", code="CS", nom="Chef de service",
                             nature="responsabilite")  # fmt: skip
        self.assertEqual(response.status_code, 302)
        entry = EntreeAudit.objects.get(objet_id=cs.pk, table__model="fonction",
                                        action="modification")  # fmt: skip
        self.assertEqual(
            (entry.auteur, entry.objet_libelle), (self.carriere, "CS — Chef de service")
        )

    def test_duplicate_code_shows_at_the_top(self):
        response = self.post(f"{self.URL}add/", code="jur", nom="Doublon")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.non_field_errors()
        self.assertIn("Une autre fonction porte déjà ce code", errors[0])

    def test_reversed_dates_show_next_to_the_closing_date(self):
        response = self.post(f"{self.URL}add/", code="X", nom="X", date_fermeture="2019-01-01")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])

    def test_editor_cannot_delete(self):
        response = self.client.post(f"{self.URL}{self.jur.pk}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Fonction.objects.filter(pk=self.jur.pk).exists())

    def test_other_profiles_cannot_open_the_admin_pages(self):
        self.client.force_login(self.remuneration)
        self.assertEqual(self.client.get(self.URL).status_code, 403)


class TypeContratAdminTests(TestCase):
    """Contract types in Django admin (contract types D12, D14)."""

    URL = "/admin/referentiels/typecontrat/"

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.cdi = TypeContrat.objects.create(
            code="CDI", nom="Contrat à durée indéterminée", duree_determinee=False,
            periode_essai=True, date_ouverture=D2015,
        )  # fmt: skip

    def setUp(self):
        self.client.force_login(self.carriere)

    def post(self, url, **values):
        data = {"code": "", "nom": "", "date_ouverture": "2020-01-01", "date_fermeture": "",
                **values}  # fmt: skip
        return self.client.post(url, data)

    def test_list_filters_search_and_help_texts(self):
        queries = ("", "?duree_determinee__exact=1", "?periode_essai__exact=0",
                   "?statut=ouvert", "?q=cdi")  # fmt: skip
        for query in queries:
            with self.subTest(query):
                self.assertEqual(self.client.get(self.URL + query).status_code, 200)
        self.assertContains(self.client.get(self.URL + "?q=indéterm"), "CDI")
        page = self.client.get(f"{self.URL}add/")
        self.assertContains(page, "doit avoir une date de fin")
        self.assertContains(page, "peut comporter une période d")

    def test_editor_adds_and_corrects_a_type(self):
        # An unticked checkbox is absent from the form data: the flag is False.
        response = self.post(f"{self.URL}add/", code="cdd", nom="Contrat a duree determinee",
                             duree_determinee="on", periode_essai="on")  # fmt: skip
        self.assertEqual(response.status_code, 302)
        cdd = TypeContrat.objects.get(code="CDD")
        self.assertEqual((cdd.duree_determinee, cdd.periode_essai), (True, True))
        self.assertEqual((cdd.cree_par, cdd.modifie_par), (self.carriere, self.carriere))

        response = self.post(f"{self.URL}{cdd.pk}/change/", code="CDD",
                             nom="Contrat à durée déterminée", duree_determinee="on",
                             periode_essai="on")  # fmt: skip
        self.assertEqual(response.status_code, 302)
        entry = EntreeAudit.objects.get(objet_id=cdd.pk, table__model="typecontrat",
                                        action="modification")  # fmt: skip
        self.assertEqual(
            (entry.auteur, entry.objet_libelle), (self.carriere, "CDD — Contrat à durée déterminée")
        )

    def test_duplicate_code_shows_at_the_top(self):
        response = self.post(f"{self.URL}add/", code="cdi", nom="Doublon")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.non_field_errors()
        self.assertIn("Un autre type de contrat porte déjà ce code", errors[0])

    def test_reversed_dates_show_next_to_the_closing_date(self):
        response = self.post(f"{self.URL}add/", code="X", nom="X", date_fermeture="2019-01-01")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("postérieure à la date d'ouverture", errors["date_fermeture"][0])

    def test_editor_cannot_delete(self):
        response = self.client.post(f"{self.URL}{self.cdi.pk}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(TypeContrat.objects.filter(pk=self.cdi.pk).exists())

    def test_other_profiles_cannot_open_the_admin_pages(self):
        self.client.force_login(self.remuneration)
        self.assertEqual(self.client.get(self.URL).status_code, 403)


class PiecesAdminTests(TestCase):
    """Document types and required documents in Django admin (document types D14, D16)."""

    TYPES = "/admin/referentiels/typedocument/"
    PIECES = "/admin/referentiels/piecerequise/"

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.dec = TypeDocument.objects.create(code="DEC", nom="Décision", date_ouverture=D2020)
        cls.ama = TypeDocument.objects.create(
            code="AMA", nom="Acte de mariage", date_ouverture=D2015
        )
        cls.req = PieceRequise.objects.create(
            evenement="promotion", type_document=cls.dec, obligatoire=True, date_ouverture=D2020
        )

    def setUp(self):
        self.client.force_login(self.carriere)

    def test_lists_filters_and_search_open(self):
        urls = (self.TYPES, self.TYPES + "?statut=ouvert", self.TYPES + "?q=dec",
                self.PIECES, self.PIECES + "?evenement__exact=promotion",
                self.PIECES + "?obligatoire__exact=1", self.PIECES + "?q=décision")  # fmt: skip
        for url in urls:
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(self.PIECES + "?q=décision"), "Promotion")

    def test_editor_adds_a_type_and_a_requirement(self):
        response = self.client.post(f"{self.TYPES}add/", {
            "code": "ana", "nom": "Acte de naissance", "date_ouverture": "2015-01-01",
            "date_fermeture": ""})  # fmt: skip
        self.assertEqual(response.status_code, 302)
        ana = TypeDocument.objects.get(code="ANA")
        self.assertEqual(ana.cree_par, self.carriere)

        response = self.client.post(f"{self.PIECES}add/", {
            "evenement": "naissance", "type_document": ana.pk, "obligatoire": "on",
            "date_ouverture": "2015-01-01", "date_fermeture": ""})  # fmt: skip
        self.assertEqual(response.status_code, 302)
        req = PieceRequise.objects.get(evenement="naissance")
        self.assertTrue(req.obligatoire)
        entry = EntreeAudit.objects.get(table__model="piecerequise", objet_id=req.pk)
        self.assertEqual((entry.auteur, entry.objet_libelle),
                         (self.carriere, "Naissance — ANA (obligatoire)"))  # fmt: skip

    def test_type_autocomplete_answers(self):
        response = self.client.get("/admin/autocomplete/", {
            "app_label": "referentiels", "model_name": "piecerequise",
            "field_name": "type_document", "term": "mariage"})  # fmt: skip
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["text"] for r in response.json()["results"]], ["AMA — Acte de mariage"])

    def test_event_and_type_are_read_only_on_change(self):
        page = self.client.get(f"{self.PIECES}{self.req.pk}/change/").content.decode()
        self.assertNotIn('name="evenement"', page)
        self.assertNotIn('name="type_document"', page)
        self.assertIn('name="obligatoire"', page)

        response = self.client.post(
            f"{self.PIECES}{self.req.pk}/change/",
            {"date_ouverture": "2020-01-01", "date_fermeture": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.req.refresh_from_db()
        self.assertFalse(self.req.obligatoire)  # unticked: corrected to optional
        self.assertEqual(self.req.type_document, self.dec)

    def test_rule_errors_show_next_to_the_field(self):
        response = self.client.post(f"{self.PIECES}add/", {
            "evenement": "mutation", "type_document": self.dec.pk, "obligatoire": "on",
            "date_ouverture": "2015-01-01", "date_fermeture": ""})  # fmt: skip
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("ne peut pas ouvrir avant son type de pièce", errors["date_ouverture"][0])

    def test_duplicate_requirement_shows_at_the_top(self):
        response = self.client.post(f"{self.PIECES}add/", {
            "evenement": "promotion", "type_document": self.dec.pk,
            "date_ouverture": "2021-01-01", "date_fermeture": ""})  # fmt: skip
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.non_field_errors()
        self.assertIn("exige déjà ce type de pièce", errors[0])

    def test_editor_cannot_delete(self):
        for url, obj in ((self.TYPES, self.ama), (self.PIECES, self.req)):
            with self.subTest(url):
                response = self.client.post(f"{url}{obj.pk}/delete/", {"post": "yes"})
                self.assertEqual(response.status_code, 403)
                self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())

    def test_other_profiles_cannot_open_the_admin_pages(self):
        self.client.force_login(self.remuneration)
        for url in (self.TYPES, self.PIECES):
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 403)


class SortiesAdminTests(TestCase):
    """Exit reasons and suspension types in Django admin (exit reasons D14, D16)."""

    MOTIFS = "/admin/referentiels/motifsortie/"
    SUSPENSIONS = "/admin/referentiels/typesuspension/"

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.adc = TypeDocument.objects.create(code="ADC", nom="Acte de décès", date_ouverture=D2015)
        cls.dec = TypeDocument.objects.create(code="DEC", nom="Décision", date_ouverture=D2020)
        cls.dcd = MotifSortie.objects.create(
            code="DCD", nom="Décès", type_document=cls.adc, deces=True, date_ouverture=D2015
        )
        cls.deta = TypeSuspension.objects.create(
            code="DETA", nom="Détachement", type_document=cls.dec, compte_anciennete=True,
            date_ouverture=D2020,
        )  # fmt: skip

    def setUp(self):
        self.client.force_login(self.carriere)

    def motif(self, **values):
        data = {"code": "X", "nom": "X", "type_document": self.adc.pk,
                "date_ouverture": "2015-01-01", "date_fermeture": "", **values}  # fmt: skip
        return self.client.post(f"{self.MOTIFS}add/", data)

    def test_lists_filters_and_search_open(self):
        urls = (self.MOTIFS, self.MOTIFS + "?statut=ouvert", self.MOTIFS + "?retraite__exact=1",
                self.MOTIFS + "?deces__exact=1", self.MOTIFS + "?q=déc",
                self.SUSPENSIONS, self.SUSPENSIONS + "?compte_anciennete__exact=1",
                self.SUSPENSIONS + "?statut=ferme", self.SUSPENSIONS + "?q=deta")  # fmt: skip
        for url in urls:
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(self.MOTIFS + "?deces__exact=1"), "Décès")

    def test_editor_adds_a_reason_and_a_suspension_type(self):
        response = self.motif(code="dem", nom="Démission")
        self.assertEqual(response.status_code, 302)
        dem = MotifSortie.objects.get(code="DEM")
        self.assertEqual(dem.cree_par, self.carriere)

        response = self.client.post(f"{self.SUSPENSIONS}add/", {
            "code": "dispo", "nom": "Mise en disponibilité", "type_document": self.dec.pk,
            "duree_max_mois": "24", "renouvellements_max": "1",
            "date_ouverture": "2020-01-01", "date_fermeture": ""})  # fmt: skip
        self.assertEqual(response.status_code, 302)
        dispo = TypeSuspension.objects.get(code="DISPO")
        self.assertEqual((dispo.compte_anciennete, dispo.duree_max_mois), (False, 24))
        entry = EntreeAudit.objects.get(table__model="typesuspension", objet_id=dispo.pk)
        self.assertEqual((entry.auteur, entry.objet_libelle),
                         (self.carriere, "DISPO — Mise en disponibilité"))  # fmt: skip

    def test_document_autocomplete_answers(self):
        for model in ("motifsortie", "typesuspension"):
            with self.subTest(model):
                response = self.client.get("/admin/autocomplete/", {
                    "app_label": "referentiels", "model_name": model,
                    "field_name": "type_document", "term": "décès"})  # fmt: skip
                self.assertEqual(response.status_code, 200)
                texts = [r["text"] for r in response.json()["results"]]
                self.assertEqual(texts, ["ADC — Acte de décès"])

    def test_retirement_and_death_shows_next_to_death(self):
        response = self.motif(retraite="on", deces="on")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("à la fois une retraite et un décès", errors["deces"][0])

    def test_opening_before_the_document_shows_next_to_the_opening_date(self):
        response = self.client.post(f"{self.SUSPENSIONS}add/", {
            "code": "X", "nom": "X", "type_document": self.dec.pk,
            "date_ouverture": "2015-01-01", "date_fermeture": ""})  # fmt: skip
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("ne peut pas ouvrir avant son type de pièce", errors["date_ouverture"][0])

    def test_zero_months_shows_next_to_the_duration(self):
        response = self.client.post(f"{self.SUSPENSIONS}add/", {
            "code": "X", "nom": "X", "type_document": self.dec.pk, "duree_max_mois": "0",
            "date_ouverture": "2020-01-01", "date_fermeture": ""})  # fmt: skip
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("au moins un mois", errors["duree_max_mois"][0])

    def test_duplicate_open_code_shows_at_the_top(self):
        response = self.motif(code="dcd", nom="Décès bis")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.non_field_errors()
        self.assertIn("porte déjà ce code", errors[0])

    def test_closing_a_document_in_use_names_the_open_rows(self):
        response = self.client.post(f"/admin/referentiels/typedocument/{self.dec.pk}/change/", {
            "code": "DEC", "nom": "Décision", "date_ouverture": "2020-01-01",
            "date_fermeture": "2025-07-01"})  # fmt: skip
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("Des types de suspension restent ouverts", errors["date_fermeture"][0])

    def test_editor_cannot_delete(self):
        for url, obj in ((self.MOTIFS, self.dcd), (self.SUSPENSIONS, self.deta)):
            with self.subTest(url):
                response = self.client.post(f"{url}{obj.pk}/delete/", {"post": "yes"})
                self.assertEqual(response.status_code, 403)
                self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())

    def test_other_profiles_cannot_open_the_admin_pages(self):
        self.client.force_login(self.remuneration)
        for url in (self.MOTIFS, self.SUSPENSIONS):
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 403)


class BanquesAdminTests(TestCase):
    """Banks in Django admin, edited by Rémunération (banks D12, D14)."""

    BANQUES = "/admin/referentiels/banque/"

    @classmethod
    def setUpTestData(cls):
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.bcf = Banque.objects.create(
            code="BCF", nom="Banque Commerciale du Fleuve", swift="BCFLCDKI", date_ouverture=D2015
        )

    def setUp(self):
        self.client.force_login(self.remuneration)

    def add(self, **values):
        data = {"code": "X", "nom": "X", "swift": "", "date_ouverture": "2015-01-01",
                "date_fermeture": "", **values}  # fmt: skip
        return self.client.post(f"{self.BANQUES}add/", data)

    def test_lists_filter_and_search_open(self):
        urls = (self.BANQUES, self.BANQUES + "?statut=ouvert", self.BANQUES + "?statut=ferme",
                self.BANQUES + "?q=fleuve", self.BANQUES + "?q=bcfl")  # fmt: skip
        for url in urls:
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(self.BANQUES + "?q=bcfl"), "Banque Commerciale")

    def test_remuneration_adds_a_bank_and_is_its_author(self):
        response = self.add(code="trc", nom="Trésor Crédit", swift="trcrcdki")
        self.assertEqual(response.status_code, 302)
        trc = Banque.objects.get(code="TRC")
        self.assertEqual((trc.swift, trc.cree_par), ("TRCRCDKI", self.remuneration))
        entry = EntreeAudit.objects.get(table__model="banque", objet_id=trc.pk)
        self.assertEqual((entry.auteur, entry.objet_libelle),
                         (self.remuneration, "TRC — Trésor Crédit"))  # fmt: skip

    def test_wrong_swift_shows_next_to_its_field(self):
        response = self.add(swift="ABC")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("Code SWIFT/BIC invalide", errors["swift"][0])

    def test_duplicate_open_code_shows_at_the_top(self):
        response = self.add(code="bcf", nom="Bis")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.non_field_errors()
        self.assertIn("porte déjà ce code", errors[0])

    def test_remuneration_cannot_delete_nor_open_other_tables(self):
        response = self.client.post(f"{self.BANQUES}{self.bcf.pk}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Banque.objects.filter(pk=self.bcf.pk).exists())
        self.assertEqual(self.client.get("/admin/referentiels/fonction/").status_code, 403)

    def test_gestion_de_carriere_cannot_open_the_bank_pages(self):
        self.client.force_login(self.carriere)
        self.assertEqual(self.client.get(self.BANQUES).status_code, 403)
        self.assertEqual(self.client.get(f"{self.BANQUES}add/").status_code, 403)
        self.assertEqual(self.client.get("/admin/referentiels/fonction/").status_code, 200)


class ParametresAdminTests(TestCase):
    """General parameters in Django admin (general parameters D12, D14)."""

    PARAMETRES = "/admin/referentiels/parametre/"

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.age = Parametre.objects.create(cle="age_limite_enfant", valeur=25, date_ouverture=D2015)

    def setUp(self):
        self.client.force_login(self.carriere)

    def add(self, **values):
        data = {"cle": "age_retraite", "valeur": "65", "date_ouverture": "2015-01-01",
                "date_fermeture": "", **values}  # fmt: skip
        return self.client.post(f"{self.PARAMETRES}add/", data)

    def test_list_and_filters_open(self):
        urls = (self.PARAMETRES, self.PARAMETRES + "?cle__exact=age_limite_enfant",
                self.PARAMETRES + "?statut=ouvert")  # fmt: skip
        for url in urls:
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(self.PARAMETRES), "Âge limite des enfants à charge")

    def test_editor_adds_a_value_and_is_its_author(self):
        self.assertEqual(self.add().status_code, 302)
        row = Parametre.objects.get(cle="age_retraite")
        self.assertEqual(row.cree_par, self.carriere)
        entry = EntreeAudit.objects.get(table__model="parametre", objet_id=row.pk)
        self.assertEqual((entry.auteur, entry.objet_libelle),
                         (self.carriere, "Âge de la retraite : 65 ans"))  # fmt: skip

    def test_out_of_bounds_shows_next_to_the_value(self):
        response = self.add(valeur="650")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertEqual(errors["valeur"], ["Entre 55 et 75 ans."])

    def test_overlapping_value_shows_at_the_top(self):
        response = self.add(cle="age_limite_enfant", valeur="21", date_ouverture="2020-01-01")
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.non_field_errors()
        self.assertIn("a déjà une valeur", errors[0])

    def test_key_is_read_only_on_change(self):
        page = self.client.get(f"{self.PARAMETRES}{self.age.pk}/change/").content.decode()
        self.assertNotIn('name="cle"', page)
        self.assertIn('name="valeur"', page)
        response = self.client.post(f"{self.PARAMETRES}{self.age.pk}/change/", {
            "cle": "age_retraite", "valeur": "24", "date_ouverture": "2015-01-01",
            "date_fermeture": ""})  # fmt: skip
        self.assertEqual(response.status_code, 302)
        self.age.refresh_from_db()
        self.assertEqual((self.age.cle, self.age.valeur), ("age_limite_enfant", 24))

    def test_editor_cannot_delete(self):
        response = self.client.post(f"{self.PARAMETRES}{self.age.pk}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Parametre.objects.filter(pk=self.age.pk).exists())

    def test_other_profiles_cannot_open_the_admin_pages(self):
        self.client.force_login(self.remuneration)
        self.assertEqual(self.client.get(self.PARAMETRES).status_code, 403)


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


class ClassificationApiTests(TestCase):
    """GET /api/referentiels/{categories,grades,echelons}/ (classification D24 to D26)."""

    @classmethod
    def setUpTestData(cls):
        cls.am = Categorie.objects.create(code="AM", nom="Maîtrise", rang=2, date_ouverture=D2015)
        cls.cd = Categorie.objects.create(code="CD", nom="Cadres", rang=4, date_ouverture=D2015)
        cls.m1 = Grade.objects.create(
            code="M1", nom="Agent de maîtrise", categorie=cls.am, rang=1, date_ouverture=D2015
        )
        cls.a2 = Grade.objects.create(
            code="A2", nom="Attaché 2", categorie=cls.cd, rang=1, date_ouverture=D2015
        )
        # A1 reformed on 2020-01-01: the old grade and its échelon close, a successor opens.
        cls.old = Grade.objects.create(
            code="A1", nom="Attaché (ancien)", categorie=cls.cd, rang=2,
            date_ouverture=D2015, date_fermeture=D2020,
        )  # fmt: skip
        cls.old_step = Echelon.objects.create(
            grade=cls.old, numero=1, date_ouverture=D2015, date_fermeture=D2020
        )
        cls.new = Grade.objects.create(
            code="A1", nom="Attaché (réformé)", categorie=cls.cd, rang=2, date_ouverture=D2020
        )
        cls.steps = [
            Echelon.objects.create(grade=g, numero=n, date_ouverture=D2020)
            for g, n in ((cls.a2, 2), (cls.new, 1), (cls.a2, 1), (cls.m1, 1))
        ]
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def get(self, url, user="Auditeur", **params):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client.get(url, params)

    def ids(self, url, **params):
        return [row["id"] for row in self.get(url, **params).json()]

    def test_access(self):
        for url in CLASSIFICATION:
            with self.subTest(url):
                self.assertEqual(self.get(url, None).status_code, 401)
                self.assertEqual(self.get(url, self.nobody).status_code, 403)
                for name in self.users:
                    self.assertEqual(self.get(url, name).status_code, 200, name)

    def test_open_today_by_default_at_a_date_or_all(self):
        self.assertNotIn(self.old.pk, self.ids(GRADES))
        self.assertIn(self.new.pk, self.ids(GRADES))

        past = self.ids(GRADES, date="2019-12-31")
        self.assertIn(self.old.pk, past)
        self.assertNotIn(self.new.pk, past)
        self.assertEqual(self.ids(ECHELONS, date="2019-12-31"), [self.old_step.pk])

        everything = self.ids(GRADES, toutes="1")
        self.assertTrue({self.old.pk, self.new.pk} <= set(everything))
        self.assertEqual(len(self.ids(ECHELONS, toutes="1")), 5)

    def test_grid_order(self):
        self.assertEqual(self.ids(CATEGORIES), [self.cd.pk, self.am.pk])
        self.assertEqual(self.ids(GRADES), [self.new.pk, self.a2.pk, self.m1.pk])
        self.assertEqual(
            [row["libelle"] for row in self.get(ECHELONS).json()],
            ["A1 — Échelon 1", "A2 — Échelon 1", "A2 — Échelon 2", "M1 — Échelon 1"],
        )

    def test_fields(self):
        cat = next(r for r in self.get(CATEGORIES).json() if r["id"] == self.cd.pk)
        self.assertEqual(
            {k: cat[k] for k in ("code", "nom", "rang", "date_ouverture", "date_fermeture")},
            {"code": "CD", "nom": "Cadres", "rang": 4, "date_ouverture": "2015-01-01",
             "date_fermeture": None},
        )  # fmt: skip
        self.assertIn("date_modification", cat)

        grade = next(r for r in self.get(GRADES).json() if r["id"] == self.new.pk)
        self.assertEqual(
            {k: grade[k] for k in ("categorie", "code", "nom", "rang", "date_ouverture")},
            {"categorie": self.cd.pk, "code": "A1", "nom": "Attaché (réformé)", "rang": 2,
             "date_ouverture": "2020-01-01"},
        )  # fmt: skip

        step = self.get(ECHELONS).json()[0]
        self.assertEqual(
            {k: step[k] for k in ("grade", "numero", "libelle", "date_fermeture")},
            {"grade": self.new.pk, "numero": 1, "libelle": "A1 — Échelon 1",
             "date_fermeture": None},
        )  # fmt: skip
        self.assertIn("cree_par", step)

    def test_invalid_date_is_refused_per_field(self):
        for url in CLASSIFICATION:
            with self.subTest(url):
                response = self.get(url, date="31/12/2025")
                self.assertEqual(response.status_code, 400)
                self.assertIn("date", response.json())

    def test_writes_are_refused(self):
        client = APIClient()
        client.force_authenticate(self.users["Gestion de carrière"])
        for url, obj in zip(CLASSIFICATION, (self.cd, self.a2, self.steps[0]), strict=True):
            detail = f"{url}{obj.pk}/"
            with self.subTest(url):
                self.assertEqual(client.post(url, {}).status_code, 405)
                self.assertEqual(client.put(detail, {}).status_code, 405)
                self.assertEqual(client.patch(detail, {}).status_code, 405)
                self.assertEqual(client.delete(detail).status_code, 405)

    def test_query_count_does_not_grow_with_rows(self):
        def count(url):
            with CaptureQueriesContext(connection) as queries:
                self.get(url, toutes="1")
            return len(queries)

        for url in CLASSIFICATION:
            count(url)  # the first request also loads the user's permissions
        before = {url: count(url) for url in CLASSIFICATION}

        for i in range(10):
            cat = Categorie.objects.create(code=f"C{i}", nom="x", rang=10 + i, date_ouverture=D2015)
            grade = Grade.objects.create(
                code=f"G{i}", nom="x", categorie=cat, rang=1, date_ouverture=D2015
            )
            Echelon.objects.create(grade=grade, numero=1, date_ouverture=D2015)

        self.assertEqual({url: count(url) for url in CLASSIFICATION}, before)


class FonctionApiTests(TestCase):
    """GET /api/referentiels/fonctions/ (fonctions D15 to D17)."""

    @classmethod
    def setUpTestData(cls):
        def create(code, nom, nature="execution", debut=D2015, fin=None):
            return Fonction.objects.create(
                code=code, nom=nom, nature=nature, date_ouverture=debut, date_fermeture=fin
            )

        cls.jur = create("JUR", "Juriste")
        cls.cs = create("CS", "Chef de service", "responsabilite")
        cls.cpt = create("CPT", "Comptable")
        # CE renamed on 2020-01-01: the old row closes, a successor keeps the code.
        cls.old = create("CE", "Chargé d'études", fin=D2020)
        cls.new = create("CE", "Analyste", debut=D2020)
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def get(self, user="Auditeur", **params):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client.get(FONCTIONS, params)

    def ids(self, **params):
        return [row["id"] for row in self.get(**params).json()]

    def test_access(self):
        self.assertEqual(self.get(None).status_code, 401)
        self.assertEqual(self.get(self.nobody).status_code, 403)
        for name in self.users:
            with self.subTest(name):
                self.assertEqual(self.get(name).status_code, 200)

    def test_open_today_by_default_at_a_date_or_all_in_order(self):
        self.assertEqual(self.ids(), [self.cs.pk, self.new.pk, self.cpt.pk, self.jur.pk])
        self.assertEqual(
            self.ids(date="2019-12-31"), [self.cs.pk, self.old.pk, self.cpt.pk, self.jur.pk]
        )
        self.assertEqual(len(self.ids(toutes="1")), 5)

    def test_fields(self):
        row = self.get().json()[0]
        self.assertEqual(
            {k: row[k] for k in ("id", "code", "nom", "nature", "nature_libelle",
                                 "date_ouverture", "date_fermeture")},
            {"id": self.cs.pk, "code": "CS", "nom": "Chef de service",
             "nature": "responsabilite", "nature_libelle": "Responsabilité",
             "date_ouverture": "2015-01-01", "date_fermeture": None},
        )  # fmt: skip
        self.assertIn("cree_par", row)
        self.assertIn("date_modification", row)

    def test_invalid_date_is_refused_per_field(self):
        response = self.get(date="31/12/2025")
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json())

    def test_writes_are_refused(self):
        client = APIClient()
        client.force_authenticate(self.users["Gestion de carrière"])
        detail = f"{FONCTIONS}{self.jur.pk}/"
        self.assertEqual(client.post(FONCTIONS, {}).status_code, 405)
        self.assertEqual(client.put(detail, {}).status_code, 405)
        self.assertEqual(client.patch(detail, {}).status_code, 405)
        self.assertEqual(client.delete(detail).status_code, 405)


class TypeContratApiTests(TestCase):
    """GET /api/referentiels/types-contrat/ (contract types D16 to D18)."""

    @classmethod
    def setUpTestData(cls):
        def create(code, nom, fixe, essai, fin=None):
            return TypeContrat.objects.create(
                code=code, nom=nom, duree_determinee=fixe, periode_essai=essai,
                date_ouverture=D2015, date_fermeture=fin,
            )  # fmt: skip

        cls.stg = create("STG", "Stage", True, False)
        cls.cdi = create("CDI", "Contrat à durée indéterminée", False, True)
        cls.jrn = create("JRN", "Journalier", False, False)
        cls.app = create("APP", "Contrat d'apprentissage", True, False, fin=D2020)  # retired
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def get(self, user="Auditeur", **params):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client.get(TYPES_CONTRAT, params)

    def ids(self, **params):
        return [row["id"] for row in self.get(**params).json()]

    def test_access(self):
        self.assertEqual(self.get(None).status_code, 401)
        self.assertEqual(self.get(self.nobody).status_code, 403)
        for name in self.users:
            with self.subTest(name):
                self.assertEqual(self.get(name).status_code, 200)

    def test_open_today_by_default_at_a_date_or_all_by_name(self):
        self.assertEqual(self.ids(), [self.cdi.pk, self.jrn.pk, self.stg.pk])
        self.assertEqual(
            self.ids(date="2019-12-31"), [self.cdi.pk, self.app.pk, self.jrn.pk, self.stg.pk]
        )
        self.assertEqual(len(self.ids(toutes="1")), 4)

    def test_fields(self):
        row = next(r for r in self.get().json() if r["id"] == self.stg.pk)
        self.assertEqual(
            {k: row[k] for k in ("code", "nom", "duree_determinee", "periode_essai",
                                 "date_ouverture", "date_fermeture")},
            {"code": "STG", "nom": "Stage", "duree_determinee": True, "periode_essai": False,
             "date_ouverture": "2015-01-01", "date_fermeture": None},
        )  # fmt: skip
        self.assertIn("cree_par", row)
        self.assertIn("date_modification", row)

    def test_invalid_date_is_refused_per_field(self):
        response = self.get(date="31/12/2025")
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json())

    def test_writes_are_refused(self):
        client = APIClient()
        client.force_authenticate(self.users["Gestion de carrière"])
        detail = f"{TYPES_CONTRAT}{self.cdi.pk}/"
        self.assertEqual(client.post(TYPES_CONTRAT, {}).status_code, 405)
        self.assertEqual(client.put(detail, {}).status_code, 405)
        self.assertEqual(client.patch(detail, {}).status_code, 405)
        self.assertEqual(client.delete(detail).status_code, 405)


class PiecesApiTests(TestCase):
    """GET /api/referentiels/{types-document,pieces-requises}/ (document types D18, D19)."""

    @classmethod
    def setUpTestData(cls):
        def doc(code, nom, fin=None):
            return TypeDocument.objects.create(
                code=code, nom=nom, date_ouverture=D2015, date_fermeture=fin
            )

        def req(evenement, type_doc, obligatoire=True, fin=None):
            return PieceRequise.objects.create(
                evenement=evenement, type_document=type_doc, obligatoire=obligatoire,
                date_ouverture=D2015, date_fermeture=fin,
            )  # fmt: skip

        cls.dec = doc("DEC", "Décision")
        cls.ctr = doc("CTR", "Contrat signé")
        cls.cj = doc("CJ", "Extrait de casier judiciaire", fin=D2020)
        cls.formation = req("formation", cls.dec, False)
        cls.promotion = req("promotion", cls.dec)
        cls.casier = req("engagement", cls.cj, fin=D2020)
        cls.contrat = req("engagement", cls.ctr)
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def get(self, url, user="Auditeur", **params):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client.get(url, params)

    def ids(self, url, **params):
        return [row["id"] for row in self.get(url, **params).json()]

    def test_access(self):
        for url in (TYPES_DOCUMENT, PIECES):
            with self.subTest(url):
                self.assertEqual(self.get(url, None).status_code, 401)
                self.assertEqual(self.get(url, self.nobody).status_code, 403)
                for name in self.users:
                    self.assertEqual(self.get(url, name).status_code, 200, name)

    def test_open_today_by_default_at_a_date_or_all_in_order(self):
        self.assertEqual(self.ids(TYPES_DOCUMENT), [self.ctr.pk, self.dec.pk])
        self.assertEqual(self.ids(PIECES), [self.contrat.pk, self.promotion.pk, self.formation.pk])
        self.assertEqual(
            self.ids(PIECES, date="2019-12-31"),
            [self.contrat.pk, self.casier.pk, self.promotion.pk, self.formation.pk],
        )
        self.assertEqual(len(self.ids(TYPES_DOCUMENT, toutes="1")), 3)
        self.assertEqual(len(self.ids(PIECES, toutes="1")), 4)

    def test_fields(self):
        doc = next(r for r in self.get(TYPES_DOCUMENT).json() if r["id"] == self.dec.pk)
        self.assertEqual(
            {k: doc[k] for k in ("code", "nom", "date_ouverture", "date_fermeture")},
            {"code": "DEC", "nom": "Décision", "date_ouverture": "2015-01-01",
             "date_fermeture": None},
        )  # fmt: skip
        row = next(r for r in self.get(PIECES).json() if r["id"] == self.formation.pk)
        self.assertEqual(
            {k: row[k] for k in ("evenement", "evenement_libelle", "type_document",
                                 "obligatoire", "date_ouverture", "date_fermeture")},
            {"evenement": "formation", "evenement_libelle": "Formation",
             "type_document": self.dec.pk, "obligatoire": False,
             "date_ouverture": "2015-01-01", "date_fermeture": None},
        )  # fmt: skip
        self.assertIn("cree_par", row)

    def test_invalid_date_is_refused_per_field(self):
        for url in (TYPES_DOCUMENT, PIECES):
            with self.subTest(url):
                response = self.get(url, date="31/12/2025")
                self.assertEqual(response.status_code, 400)
                self.assertIn("date", response.json())

    def test_writes_are_refused(self):
        client = APIClient()
        client.force_authenticate(self.users["Gestion de carrière"])
        for url, obj in ((TYPES_DOCUMENT, self.dec), (PIECES, self.promotion)):
            detail = f"{url}{obj.pk}/"
            with self.subTest(url):
                self.assertEqual(client.post(url, {}).status_code, 405)
                self.assertEqual(client.put(detail, {}).status_code, 405)
                self.assertEqual(client.patch(detail, {}).status_code, 405)
                self.assertEqual(client.delete(detail).status_code, 405)

    def test_query_count_does_not_grow_with_requirements(self):
        def count():
            with CaptureQueriesContext(connection) as queries:
                self.get(PIECES, toutes="1")
            return len(queries)

        count()  # the first request also loads the user's permissions
        before = count()
        for i in range(10):
            doc = TypeDocument.objects.create(code=f"T{i}", nom="x", date_ouverture=D2015)
            PieceRequise.objects.create(
                evenement="mariage", type_document=doc, obligatoire=True, date_ouverture=D2015
            )
        self.assertEqual(count(), before)


class SortiesApiTests(TestCase):
    """GET /api/referentiels/motifs-sortie/ and /types-suspension/ (exit reasons D18, D19)."""

    @classmethod
    def setUpTestData(cls):
        cls.ldm = TypeDocument.objects.create(
            code="LDM", nom="Lettre de démission", date_ouverture=D2015
        )
        cls.dec = TypeDocument.objects.create(code="DEC", nom="Décision", date_ouverture=D2015)

        def motif(code, nom, **extra):
            return MotifSortie.objects.create(
                code=code, nom=nom, type_document=extra.pop("doc", cls.ldm),
                date_ouverture=extra.pop("debut", D2015), **extra,
            )  # fmt: skip

        cls.ret = motif("RET", "Retraite pour ancienneté", doc=cls.dec, retraite=True)
        cls.dem = motif("DEM", "Démission")
        # Resignation's document changed on 2020-01-01: the old row closes.
        cls.old = motif("DEMO", "Ancienne démission", date_fermeture=D2020)
        cls.dispo = TypeSuspension.objects.create(
            code="DISPO", nom="Mise en disponibilité", type_document=cls.dec,
            compte_anciennete=False, duree_max_mois=24, renouvellements_max=1,
            date_ouverture=D2015,
        )  # fmt: skip
        cls.deta = TypeSuspension.objects.create(
            code="DETA", nom="Détachement", type_document=cls.dec, compte_anciennete=True,
            date_ouverture=D2015,
        )  # fmt: skip
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def get(self, url, user="Auditeur", **params):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client.get(url, params)

    def ids(self, url, **params):
        return [row["id"] for row in self.get(url, **params).json()]

    def test_access(self):
        for url in (MOTIFS, SUSPENSIONS):
            with self.subTest(url):
                self.assertEqual(self.get(url, None).status_code, 401)
                self.assertEqual(self.get(url, self.nobody).status_code, 403)
                for name in self.users:
                    self.assertEqual(self.get(url, name).status_code, 200, name)

    def test_open_today_by_default_at_a_date_or_all_by_name(self):
        self.assertEqual(self.ids(MOTIFS), [self.dem.pk, self.ret.pk])
        self.assertEqual(
            self.ids(MOTIFS, date="2019-12-31"), [self.old.pk, self.dem.pk, self.ret.pk]
        )
        self.assertEqual(len(self.ids(MOTIFS, toutes="1")), 3)
        self.assertEqual(self.ids(SUSPENSIONS), [self.deta.pk, self.dispo.pk])
        self.assertEqual(self.ids(SUSPENSIONS, date="2014-12-31"), [])

    def test_fields(self):
        row = self.get(MOTIFS).json()[1]
        self.assertEqual(
            {k: row[k] for k in ("id", "code", "nom", "type_document", "type_document_libelle",
                                 "retraite", "deces", "date_ouverture", "date_fermeture")},
            {"id": self.ret.pk, "code": "RET", "nom": "Retraite pour ancienneté",
             "type_document": self.dec.pk, "type_document_libelle": "DEC — Décision",
             "retraite": True, "deces": False, "date_ouverture": "2015-01-01",
             "date_fermeture": None},
        )  # fmt: skip
        self.assertIn("cree_par", row)

        deta, dispo = self.get(SUSPENSIONS).json()
        keys = ("type_document_libelle", "compte_anciennete", "duree_max_mois",
                "renouvellements_max")  # fmt: skip
        self.assertEqual({k: deta[k] for k in keys}, {
            "type_document_libelle": "DEC — Décision", "compte_anciennete": True,
            "duree_max_mois": None, "renouvellements_max": None})  # fmt: skip
        self.assertEqual({k: dispo[k] for k in keys}, {
            "type_document_libelle": "DEC — Décision", "compte_anciennete": False,
            "duree_max_mois": 24, "renouvellements_max": 1})  # fmt: skip
        self.assertIn("date_modification", dispo)

    def test_invalid_date_is_refused_per_field(self):
        for url in (MOTIFS, SUSPENSIONS):
            with self.subTest(url):
                response = self.get(url, date="31/12/2025")
                self.assertEqual(response.status_code, 400)
                self.assertIn("date", response.json())

    def test_writes_are_refused(self):
        client = APIClient()
        client.force_authenticate(self.users["Gestion de carrière"])
        for url, obj in ((MOTIFS, self.dem), (SUSPENSIONS, self.deta)):
            detail = f"{url}{obj.pk}/"
            with self.subTest(url):
                self.assertEqual(client.post(url, {}).status_code, 405)
                self.assertEqual(client.put(detail, {}).status_code, 405)
                self.assertEqual(client.patch(detail, {}).status_code, 405)
                self.assertEqual(client.delete(detail).status_code, 405)

    def test_query_count_does_not_grow_with_rows(self):
        def count(url):
            with CaptureQueriesContext(connection) as queries:
                self.get(url, toutes="1")
            return len(queries)

        for url in (MOTIFS, SUSPENSIONS):
            count(url)  # the first request also loads the user's permissions
        before = {url: count(url) for url in (MOTIFS, SUSPENSIONS)}

        for i in range(10):
            doc = TypeDocument.objects.create(code=f"D{i}", nom="x", date_ouverture=D2015)
            MotifSortie.objects.create(code=f"M{i}", nom="x", type_document=doc,
                                       date_ouverture=D2015)  # fmt: skip
            TypeSuspension.objects.create(
                code=f"S{i}", nom="x", type_document=doc, compte_anciennete=False,
                date_ouverture=D2015,
            )  # fmt: skip

        self.assertEqual({url: count(url) for url in (MOTIFS, SUSPENSIONS)}, before)


class BanquesApiTests(TestCase):
    """GET /api/referentiels/banques/ (banks D16, D17)."""

    @classmethod
    def setUpTestData(cls):
        def create(code, nom, swift="", debut=D2015, fin=None):
            return Banque.objects.create(
                code=code, nom=nom, swift=swift, date_ouverture=debut, date_fermeture=fin
            )

        cls.trc = create("TRC", "Trésor Crédit")
        cls.bcf = create("BCF", "Banque Commerciale du Fleuve", "BCFLCDKI")
        # Merged on 2020-01-01: the old row closes, a successor keeps the code.
        cls.old = create("UBK", "Union des Banques du Kasaï", fin=D2020)
        cls.new = create("UBK", "Union Bank Kivu-Kasaï", "UBKKCDKIXXX", debut=D2020)
        cls.users = {name: member(slug, name) for name, (slug, _) in GROUPS.items()}
        cls.nobody = member("personne")

    def get(self, user="Auditeur", **params):
        client = APIClient()
        if user is not None:
            client.force_authenticate(self.users.get(user, user))
        return client.get(BANQUES, params)

    def ids(self, **params):
        return [row["id"] for row in self.get(**params).json()]

    def test_access(self):
        self.assertEqual(self.get(None).status_code, 401)
        self.assertEqual(self.get(self.nobody).status_code, 403)
        for name in self.users:
            with self.subTest(name):
                self.assertEqual(self.get(name).status_code, 200)

    def test_open_today_by_default_at_a_date_or_all_by_name(self):
        self.assertEqual(self.ids(), [self.bcf.pk, self.trc.pk, self.new.pk])
        self.assertEqual(self.ids(date="2019-12-31"), [self.bcf.pk, self.trc.pk, self.old.pk])
        self.assertEqual(len(self.ids(toutes="1")), 4)

    def test_fields(self):
        bcf, trc, _ = self.get().json()
        self.assertEqual(
            {k: bcf[k] for k in ("id", "code", "nom", "swift", "date_ouverture", "date_fermeture")},
            {"id": self.bcf.pk, "code": "BCF", "nom": "Banque Commerciale du Fleuve",
             "swift": "BCFLCDKI", "date_ouverture": "2015-01-01", "date_fermeture": None},
        )  # fmt: skip
        self.assertEqual(trc["swift"], "")
        self.assertIn("cree_par", bcf)
        self.assertIn("date_modification", bcf)

    def test_invalid_date_is_refused_per_field(self):
        response = self.get(date="31/12/2025")
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json())

    def test_writes_are_refused(self):
        client = APIClient()
        client.force_authenticate(self.users["Rémunération"])
        detail = f"{BANQUES}{self.bcf.pk}/"
        self.assertEqual(client.post(BANQUES, {}).status_code, 405)
        self.assertEqual(client.put(detail, {}).status_code, 405)
        self.assertEqual(client.patch(detail, {}).status_code, 405)
        self.assertEqual(client.delete(detail).status_code, 405)


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


class DemoClassificationTests(TestCase):
    """create_demo_classification (classification D31, D32)."""

    def run_command(self):
        out = StringIO()
        call_command("create_demo_classification", stdout=out)
        return out.getvalue()

    def counts(self):
        return (
            Categorie.objects.count(),
            Grade.objects.count(),
            Echelon.objects.count(),
            EntreeAudit.objects.count(),
        )

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(Categorie.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_a_valid_grid_once(self):
        output = self.run_command()

        self.assertIn("54 créés", output)  # 4 catégories, 10 grades, 40 échelons
        self.assertEqual(
            list(Categorie.objects.values_list("code", flat=True)), ["CD", "CC", "AM", "AE"]
        )
        for model in (Categorie, Grade, Echelon):
            for obj in model.objects.all():
                obj.full_clean()  # every rule holds
        today = timezone.localdate()
        self.assertEqual(Grade.objects.ouvertes(today).count(), 9)
        open_grades = Grade.objects.ouvertes(today)
        for cat in Categorie.objects.all():
            self.assertIn(open_grades.filter(categorie=cat).count(), (2, 3), cat.code)
        self.assertTrue(all(3 <= g.echelons.count() <= 5 for g in Grade.objects.all()))
        self.assertFalse(
            EntreeAudit.objects.filter(module="referentiels", table__model="grade")
            .exclude(auteur=None)
            .exists()
        )

        # The reformed grade: the old scale until 2025, the new one since, same code.
        old, new = Grade.objects.filter(code="AT2").order_by("date_ouverture")
        self.assertEqual((old.date_fermeture, new.date_ouverture), (date(2025, 1, 1),) * 2)
        self.assertEqual(old.echelons.filter(date_fermeture=date(2025, 1, 1)).count(), 3)
        self.assertEqual(Grade.objects.ouvertes(date(2024, 12, 31)).get(code="AT2"), old)
        self.assertEqual(Grade.objects.ouvertes(today).get(code="AT2"), new)
        self.assertEqual(Echelon.objects.ouvertes(today).filter(grade=new).count(), 5)

        before = self.counts()
        self.assertIn("0 créés", self.run_command())
        self.assertEqual(self.counts(), before)


class DemoFonctionsTests(TestCase):
    """create_demo_fonctions (fonctions D21, D22)."""

    def run_command(self):
        out = StringIO()
        call_command("create_demo_fonctions", stdout=out)
        return out.getvalue()

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(Fonction.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_a_valid_list_once(self):
        output = self.run_command()

        self.assertIn("13 créées", output)
        for obj in Fonction.objects.all():
            obj.full_clean()  # every rule holds
        today = timezone.localdate()
        natures = set(Fonction.objects.ouvertes(today).values_list("nature", flat=True))
        self.assertEqual(natures, {"responsabilite", "execution"})
        self.assertFalse(
            EntreeAudit.objects.filter(table__model="fonction").exclude(auteur=None).exists()
        )

        # The renamed fonction: the old name until 2024, the new one since, same code.
        old, new = Fonction.objects.filter(code="CE").order_by("date_ouverture")
        self.assertEqual((old.date_fermeture, new.date_ouverture), (date(2024, 1, 1),) * 2)
        self.assertEqual(Fonction.objects.ouvertes(date(2023, 12, 31)).get(code="CE"), old)
        self.assertEqual(Fonction.objects.ouvertes(today).get(code="CE"), new)

        before = (Fonction.objects.count(), EntreeAudit.objects.count())
        self.assertIn("0 créées", self.run_command())
        self.assertEqual((Fonction.objects.count(), EntreeAudit.objects.count()), before)


class DemoTypesContratTests(TestCase):
    """create_demo_types_contrat (contract types D22)."""

    def run_command(self):
        out = StringIO()
        call_command("create_demo_types_contrat", stdout=out)
        return out.getvalue()

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(TypeContrat.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_valid_types_once(self):
        output = self.run_command()

        self.assertIn("5 créés", output)
        for obj in TypeContrat.objects.all():
            obj.full_clean()  # every rule holds
        today = timezone.localdate()
        open_now = TypeContrat.objects.ouvertes(today)
        self.assertEqual(
            {(t.code, t.duree_determinee, t.periode_essai) for t in open_now},
            {("CDI", False, True), ("CDD", True, True), ("STG", True, False),
             ("JRN", False, False)},
        )  # fmt: skip
        # The retired type: open in 2022, gone since 2023, with no successor.
        self.assertTrue(TypeContrat.objects.ouvertes(date(2022, 6, 1)).filter(code="APP").exists())
        self.assertEqual(TypeContrat.objects.filter(code="APP").count(), 1)
        self.assertFalse(
            EntreeAudit.objects.filter(table__model="typecontrat").exclude(auteur=None).exists()
        )

        before = (TypeContrat.objects.count(), EntreeAudit.objects.count())
        self.assertIn("0 créés", self.run_command())
        self.assertEqual((TypeContrat.objects.count(), EntreeAudit.objects.count()), before)


class DemoPiecesTests(TestCase):
    """create_demo_pieces (document types D23)."""

    def run_command(self):
        out = StringIO()
        call_command("create_demo_pieces", stdout=out)
        return out.getvalue()

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(TypeDocument.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_valid_rows_once(self):
        output = self.run_command()

        self.assertIn("30 créées", output)  # 13 types, 17 requirements
        for model in (TypeDocument, PieceRequise):
            for obj in model.objects.all():
                obj.full_clean()  # every rule holds
        today = timezone.localdate()

        def hiring(day):
            return set(
                PieceRequise.objects.ouvertes(day)
                .filter(evenement="engagement", obligatoire=True)
                .values_list("type_document__code", flat=True)
            )

        self.assertEqual(hiring(today), {"CTR", "CNI", "DIP"})
        self.assertEqual(hiring(date(2023, 6, 1)), {"CTR", "CNI", "DIP", "CJ"})
        self.assertFalse(PieceRequise.objects.filter(evenement="sortie").exists())
        self.assertGreater(PieceRequise.objects.filter(type_document__code="DEC").count(), 1)
        self.assertEqual(
            set(PieceRequise.objects.values_list("obligatoire", flat=True)), {True, False}
        )
        self.assertFalse(
            EntreeAudit.objects.filter(table__model__in=["typedocument", "piecerequise"])
            .exclude(auteur=None)
            .exists()
        )

        before = (PieceRequise.objects.count(), EntreeAudit.objects.count())
        self.assertIn("0 créées", self.run_command())
        self.assertEqual((PieceRequise.objects.count(), EntreeAudit.objects.count()), before)


class DemoSortiesTests(TestCase):
    """create_demo_sorties (exit reasons D23)."""

    def run_command(self):
        out = StringIO()
        call_command("create_demo_sorties", stdout=out)
        return out.getvalue()

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(TypeDocument.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_valid_rows_once(self):
        output = self.run_command()

        self.assertIn("Pièces de démonstration prêtes", output)  # ran create_demo_pieces
        self.assertIn("6 créés", output)  # 4 reasons, 2 suspension types
        for model in (MotifSortie, TypeSuspension):
            for obj in model.objects.all():
                obj.full_clean()  # every rule holds

        motifs = {m.code: m for m in MotifSortie.objects.select_related("type_document")}
        self.assertEqual({c for c, m in motifs.items() if m.retraite}, {"RET-ANC", "RET-AGE"})
        self.assertEqual({c for c, m in motifs.items() if m.deces}, {"DCD"})
        self.assertFalse(motifs["DEM"].retraite or motifs["DEM"].deces)
        self.assertEqual(
            {c: m.type_document.code for c, m in motifs.items()},
            {"RET-ANC": "DRT", "RET-AGE": "DRT", "DEM": "LDM", "DCD": "ADC"},
        )

        dispo = TypeSuspension.objects.get(code="DISPO")
        deta = TypeSuspension.objects.get(code="DETA")
        self.assertEqual(
            (dispo.compte_anciennete, dispo.duree_max_mois, dispo.renouvellements_max),
            (False, 24, 1),
        )
        self.assertEqual(
            (deta.compte_anciennete, deta.duree_max_mois, deta.renouvellements_max),
            (True, None, None),
        )
        self.assertEqual(dispo.type_document, deta.type_document)
        self.assertEqual(deta.type_document.code, "DEC")
        self.assertFalse(
            EntreeAudit.objects.filter(table__model__in=["motifsortie", "typesuspension"])
            .exclude(auteur=None)
            .exists()
        )

        before = (MotifSortie.objects.count(), EntreeAudit.objects.count())
        self.assertIn("0 créés", self.run_command())
        self.assertEqual((MotifSortie.objects.count(), EntreeAudit.objects.count()), before)


class DemoBanquesTests(TestCase):
    """create_demo_banques (banks D21)."""

    def run_command(self):
        out = StringIO()
        call_command("create_demo_banques", stdout=out)
        return out.getvalue()

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(Banque.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_valid_rows_once(self):
        self.assertIn("7 créées", self.run_command())
        for obj in Banque.objects.all():
            obj.full_clean()  # every rule holds

        self.assertEqual(Banque.objects.filter(swift="").count(), 1)
        old, new = Banque.objects.filter(code="UBK").order_by("date_ouverture")
        self.assertEqual(old.date_fermeture, new.date_ouverture)
        self.assertNotEqual(old.nom, new.nom)
        today = Banque.objects.ouvertes(timezone.localdate())
        self.assertEqual(today.count(), 6)
        self.assertNotIn(old, today)
        self.assertFalse(
            EntreeAudit.objects.filter(table__model="banque").exclude(auteur=None).exists()
        )

        before = (Banque.objects.count(), EntreeAudit.objects.count())
        self.assertIn("0 créées", self.run_command())
        self.assertEqual((Banque.objects.count(), EntreeAudit.objects.count()), before)
