"""Who edits agents, their contact details, contracts, assignments,
classifications and bank accounts, and the Django admin (agent identity D14 to
D16, contact details D15, D16, contract D16, D17, position history D17, D18,
bank account D16, D17)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.accounts.roles import (
    AFFECTATION_EDIT_PERMISSIONS,
    AGENT_DOCUMENT_EDIT_PERMISSIONS,
    AGENT_EDIT_PERMISSIONS,
    CLASSEMENT_EDIT_PERMISSIONS,
    COMPTE_BANCAIRE_EDIT_PERMISSIONS,
    CONTRAT_EDIT_PERMISSIONS,
    COORDONNEES_EDIT_PERMISSIONS,
    PIECE_JOINTE_EDIT_PERMISSIONS,
    sync_groups,
)
from apps.audit.models import EntreeAudit
from apps.referentiels.models import (
    Banque,
    Categorie,
    Echelon,
    Fonction,
    Grade,
    Site,
    TypeContrat,
    UniteOrganisationnelle,
)

from .models import (
    AFFECTATION_DATE_PRISE,
    COMPTE_DATE_PRISE,
    CONTRAT_OVERLAP,
    ESSAI_INTERDIT,
    FIN_OBLIGATOIRE,
    HORS_CONTRAT,
    MATRICULE_TAKEN,
    NUMERO_HELP,
    NUMERO_PRIS,
    PHONE_HELP,
    URGENCE_PAIR,
    Affectation,
    Agent,
    Classement,
    CompteBancaire,
    Contrat,
    Coordonnees,
)
from .test_affectations import D2015

EDITORS = {"Gestion de carrière", "Chef de service — Gestion de carrière"}
PAIE_EDITORS = {"Rémunération", "Chef de service — Rémunération"}


def inline(initial=0, **row):
    """The contact details inline of the agent page: empty, or one row (D16)."""
    data = {
        "coordonnees-TOTAL_FORMS": "1" if row or initial else "0",
        "coordonnees-INITIAL_FORMS": str(initial),
        "coordonnees-MIN_NUM_FORMS": "0",
        "coordonnees-MAX_NUM_FORMS": "1",
    }
    data.update({f"coordonnees-0-{name}": value for name, value in row.items()})
    return {
        **data,
        **contrats(),
        **formset("affectations"),
        **formset("classements"),
    }


def formset(prefix, *rows, initial=0):
    """A tabular inline of the agent page: its management fields and rows. The
    first `initial` rows are existing ones, carrying their id."""
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(rows)),
        f"{prefix}-INITIAL_FORMS": str(initial),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for index, row in enumerate(rows):
        data.update({f"{prefix}-{index}-{name}": value for name, value in row.items()})
    return data


def contrats(*rows, initial=0):
    """The contracts inline of the agent page (contract D17)."""
    return formset("contrats", *rows, initial=initial)


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
                # Rémunération views the agents to pick one (bank account D16).
                expected = EDITORS | PAIE_EDITORS if permission.endswith("view_agent") else EDITORS
                self.assertEqual(holders(permission), expected)

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
        self.assertEqual(
            holders("agents.view_agent"), EDITORS | PAIE_EDITORS | {"Administration du personnel"}
        )


class CoordonneesPermissionTests(TestCase):
    def test_editors_hold_view_add_change_and_nobody_deletes(self):
        self.assertEqual(len(COORDONNEES_EDIT_PERMISSIONS), 3)
        for permission in COORDONNEES_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(holders(permission), EDITORS)
        self.assertFalse(Permission.objects.filter(codename="delete_coordonnees").exists())

    def test_group_setup_regrants_and_keeps_hand_made_ones(self):
        carriere = Group.objects.get(name="Gestion de carrière")
        carriere.permissions.remove(*Permission.objects.filter(codename__endswith="_coordonnees"))
        personnel = Group.objects.get(name="Administration du personnel")
        personnel.permissions.add(Permission.objects.get(codename="change_coordonnees"))

        sync_groups()

        self.assertEqual(holders("agents.add_coordonnees"), EDITORS)
        self.assertEqual(
            holders("agents.change_coordonnees"), EDITORS | {"Administration du personnel"}
        )


class ContratPermissionTests(TestCase):
    def test_editors_hold_view_add_change_and_nobody_deletes(self):
        self.assertEqual(len(CONTRAT_EDIT_PERMISSIONS), 3)
        for permission in CONTRAT_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(holders(permission), EDITORS)
        self.assertFalse(Permission.objects.filter(codename="delete_contrat").exists())

    def test_group_setup_regrants_and_keeps_hand_made_ones(self):
        chef = Group.objects.get(name="Chef de service — Gestion de carrière")
        chef.permissions.remove(*Permission.objects.filter(codename__endswith="_contrat"))
        remuneration = Group.objects.get(name="Rémunération")
        remuneration.permissions.add(Permission.objects.get(codename="view_contrat"))

        sync_groups()

        self.assertEqual(holders("agents.add_contrat"), EDITORS)
        self.assertEqual(holders("agents.view_contrat"), EDITORS | {"Rémunération"})


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
            **inline(),
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
            "nationalite": "Congolaise", **inline()})  # fmt: skip
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
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.AGENTS).status_code, 403)
        self.assertEqual(self.client.get(f"{self.AGENTS}add/").status_code, 403)

    def test_remuneration_sees_the_agents_read_only(self):
        """Rémunération views agents to pick one for an account (bank account D16)."""
        self.client.force_login(self.remuneration)
        url = f"{self.AGENTS}{self.kabila.pk}/change/"
        self.assertContains(self.client.get(self.AGENTS), "ARPTC/0001/2010")
        page = self.client.get(url).content.decode()
        self.assertNotIn('name="nom"', page)
        self.assertEqual(self.client.get(f"{self.AGENTS}add/").status_code, 403)
        response = self.client.post(url, {"nom": "Autre", **inline()})
        self.assertEqual(response.status_code, 403)
        self.kabila.refresh_from_db()
        self.assertEqual(self.kabila.nom, "Kabila")


class CoordonneesInlineTests(TestCase):
    """The contact details inline on the agent page (contact details D16)."""

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.agent = Agent.objects.create(
            matricule="ARPTC/0004/2011",
            nom="Mbuyi",
            prenom="Esther",
            sexe="F",
            date_naissance=date(1984, 12, 11),
            lieu_naissance="Mbuji-Mayi",
        )
        cls.url = f"/admin/agents/agent/{cls.agent.pk}/change/"

    def setUp(self):
        self.client.force_login(self.carriere)

    def post(self, initial=0, **row):
        row = {"agent": str(self.agent.pk), "adresse": "Avenue Kasa-Vubu 40",
               "commune": "Kalamu", "ville": "Kinshasa", "telephone": "0812345678",
               **row}  # fmt: skip
        data = {
            "nom": "Mbuyi", "postnom": "", "prenom": "Esther", "sexe": "F",
            "date_naissance": "1984-12-11", "lieu_naissance": "Mbuji-Mayi",
            "nationalite": "Congolaise", **inline(initial, **row),
        }  # fmt: skip
        return self.client.post(self.url, data)

    def test_editor_adds_contact_details_and_is_their_author(self):
        response = self.post(telephone=" +243  81 234 5678 ")
        self.assertEqual(response.status_code, 302)
        row = Coordonnees.objects.get(agent=self.agent)
        self.assertEqual((row.telephone, row.cree_par, row.modifie_par),
                         ("+243 81 234 5678", self.carriere, self.carriere))  # fmt: skip
        entry = EntreeAudit.objects.get(table__model="coordonnees", objet_id=row.pk)
        self.assertEqual(
            (entry.action, entry.auteur, entry.objet_libelle),
            ("creation", self.carriere, "Coordonnées de ARPTC/0004/2011 — Mbuyi Esther"),
        )

    def test_correction_is_stamped_with_the_editor(self):
        row = Coordonnees.objects.create(agent=self.agent, adresse="Av. 1", ville="Kinshasa",
                                         telephone="0812345678")  # fmt: skip
        response = self.post(initial=1, id=str(row.pk), courriel=" Esther@Example.CD ")
        self.assertEqual(response.status_code, 302)
        row.refresh_from_db()
        self.assertEqual((row.courriel, row.cree_par, row.modifie_par),
                         ("esther@example.cd", None, self.carriere))  # fmt: skip
        entry = EntreeAudit.objects.get(
            table__model="coordonnees", objet_id=row.pk, action="modification"
        )
        self.assertEqual(entry.auteur, self.carriere)

    def test_rule_errors_show_next_to_their_field(self):
        response = self.post(telephone="08A1234567", urgence_nom="Nsimba")
        self.assertEqual(response.status_code, 200)
        errors = response.context["inline_admin_formsets"][0].formset.forms[0].errors
        self.assertEqual(errors["telephone"], [PHONE_HELP])
        self.assertEqual(errors["urgence_telephone"], [URGENCE_PAIR])
        self.assertFalse(Coordonnees.objects.exists())

    def test_one_row_at_most_and_no_delete_box(self):
        Coordonnees.objects.create(agent=self.agent, adresse="Av. 1", ville="Kinshasa",
                                   telephone="0812345678")  # fmt: skip
        response = self.client.get(self.url)
        formset = response.context["inline_admin_formsets"][0].formset
        self.assertEqual((formset.max_num, len(formset.forms)), (1, 1))
        self.assertFalse(formset.can_delete)
        self.assertNotContains(response, "coordonnees-0-DELETE")

    def test_inline_is_hidden_without_the_permission(self):
        Group.objects.get(name="Gestion de carrière").permissions.remove(
            *Permission.objects.filter(codename__endswith="_coordonnees")
        )
        self.assertNotContains(self.client.get(self.url), "coordonnees-TOTAL_FORMS")


class ContratInlineTests(TestCase):
    """The contracts inline on the agent page (contract D17)."""

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.cdi = TypeContrat.objects.create(
            code="CDI",
            nom="CDI",
            duree_determinee=False,
            periode_essai=True,
            date_ouverture=date(2015, 1, 1),
        )
        cls.cdd = TypeContrat.objects.create(
            code="CDD",
            nom="CDD",
            duree_determinee=True,
            periode_essai=True,
            date_ouverture=date(2015, 1, 1),
        )
        cls.stage = TypeContrat.objects.create(
            code="STG",
            nom="Stage",
            duree_determinee=True,
            periode_essai=False,
            date_ouverture=date(2015, 1, 1),
        )
        cls.agent = Agent.objects.create(
            matricule="ARPTC/0007/2015",
            nom="Tshibangu",
            prenom="Didier",
            sexe="M",
            date_naissance=date(1979, 11, 19),
            lieu_naissance="Kinshasa",
        )
        cls.url = f"/admin/agents/agent/{cls.agent.pk}/change/"

    def setUp(self):
        self.client.force_login(self.carriere)

    def row(self, type_contrat, debut, fin="", essai="", **extra):
        return {
            "agent": str(self.agent.pk),
            "type_contrat": str(type_contrat.pk),
            "date_debut": debut,
            "date_fin": fin,
            "fin_periode_essai": essai,
            **extra,
        }

    def post(self, *rows, initial=0):
        data = {
            "nom": "Tshibangu",
            "postnom": "",
            "prenom": "Didier",
            "sexe": "M",
            "date_naissance": "1979-11-19",
            "lieu_naissance": "Kinshasa",
            "nationalite": "Congolaise",
            **inline(),
            **contrats(*rows, initial=initial),
        }
        return self.client.post(self.url, data)

    def row_errors(self, response, index=0):
        formset = next(
            f.formset
            for f in response.context["inline_admin_formsets"]
            if f.formset.prefix == "contrats"
        )
        return formset.forms[index].errors

    def test_editor_adds_a_cdd_then_its_renewal_and_is_their_author(self):
        response = self.post(self.row(self.cdd, "2020-03-01", "2021-02-28", "2020-05-31"))
        self.assertEqual(response.status_code, 302)
        first = Contrat.objects.get(agent=self.agent)

        response = self.post(
            self.row(self.cdd, "2020-03-01", "2021-02-28", "2020-05-31", id=str(first.pk)),
            self.row(self.cdd, "2021-03-01", "2022-02-28"),
            initial=1,
        )
        self.assertEqual(response.status_code, 302)
        rows = list(self.agent.contrats.all())
        self.assertEqual(
            [(c.date_debut, c.date_fin) for c in rows],
            [(date(2020, 3, 1), date(2021, 2, 28)), (date(2021, 3, 1), date(2022, 2, 28))],
        )
        self.assertEqual({c.cree_par for c in rows}, {self.carriere})
        entries = EntreeAudit.objects.filter(table__model="contrat", action="creation")
        self.assertEqual(
            set(entries.values_list("auteur", "objet_libelle")),
            {
                (self.carriere.pk, "CDD du 01/03/2020 au 28/02/2021 — ARPTC/0007/2015"),
                (self.carriere.pk, "CDD du 01/03/2021 au 28/02/2022 — ARPTC/0007/2015"),
            },
        )

    def test_rule_errors_show_next_to_their_field(self):
        response = self.post(self.row(self.cdd, "2020-03-01"))
        self.assertEqual(self.row_errors(response)["date_fin"], [FIN_OBLIGATOIRE])
        response = self.post(self.row(self.stage, "2020-03-01", "2020-08-31", "2020-04-30"))
        self.assertEqual(self.row_errors(response)["fin_periode_essai"], [ESSAI_INTERDIT])
        self.assertFalse(Contrat.objects.exists())

    def test_overlap_shows_on_the_row(self):
        existing = Contrat.objects.create(
            agent=self.agent,
            type_contrat=self.cdd,
            date_debut=date(2020, 3, 1),
            date_fin=date(2021, 2, 28),
        )
        response = self.post(
            self.row(self.cdd, "2020-03-01", "2021-02-28", id=str(existing.pk)),
            self.row(self.cdi, "2021-02-28"),
            initial=1,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.row_errors(response, 1).get("__all__"), [CONTRAT_OVERLAP])
        self.assertEqual(Contrat.objects.count(), 1)

    def test_rows_in_date_order_one_empty_row_and_no_delete_box(self):
        later = Contrat.objects.create(
            agent=self.agent, type_contrat=self.cdi, date_debut=date(2021, 3, 1)
        )
        earlier = Contrat.objects.create(
            agent=self.agent,
            type_contrat=self.cdd,
            date_debut=date(2020, 3, 1),
            date_fin=date(2021, 2, 28),
        )
        response = self.client.get(self.url)
        formset = next(
            f.formset
            for f in response.context["inline_admin_formsets"]
            if f.formset.prefix == "contrats"
        )
        self.assertEqual([f.instance.pk for f in formset.forms[:2]], [earlier.pk, later.pk])
        self.assertEqual(len(formset.forms), 3)  # two contracts and one empty row
        self.assertFalse(formset.can_delete)
        self.assertNotContains(response, "contrats-0-DELETE")

    def test_inline_is_hidden_without_the_permission(self):
        Group.objects.get(name="Gestion de carrière").permissions.remove(
            *Permission.objects.filter(codename__endswith="_contrat")
        )
        self.assertNotContains(self.client.get(self.url), "contrats-TOTAL_FORMS")


class PositionPermissionTests(TestCase):
    """Assignments and classifications (position history D17)."""

    def test_editors_hold_view_add_change_and_nobody_deletes(self):
        for model, permissions in (
            ("affectation", AFFECTATION_EDIT_PERMISSIONS),
            ("classement", CLASSEMENT_EDIT_PERMISSIONS),
        ):
            self.assertEqual(len(permissions), 3)
            for permission in permissions:
                with self.subTest(permission):
                    self.assertEqual(holders(permission), EDITORS)
            self.assertFalse(Permission.objects.filter(codename=f"delete_{model}").exists())

    def test_group_setup_regrants_and_keeps_hand_made_ones(self):
        chef = Group.objects.get(name="Chef de service — Gestion de carrière")
        chef.permissions.remove(
            *Permission.objects.filter(codename__in=["add_affectation", "change_classement"])
        )
        paie = Group.objects.get(name="Rémunération")
        paie.permissions.add(Permission.objects.get(codename="view_classement"))

        sync_groups()

        self.assertEqual(holders("agents.add_affectation"), EDITORS)
        self.assertEqual(holders("agents.change_classement"), EDITORS)
        self.assertEqual(holders("agents.view_classement"), EDITORS | {"Rémunération"})


class PositionInlineTests(TestCase):
    """The assignments and classifications inlines on the agent page (position
    history D18). The agent is under a CDI from 01/03/2020."""

    @classmethod
    def setUpTestData(cls):
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        d2015 = date(2015, 1, 1)
        site = Site.objects.create(code="KIN", nom="Kinshasa", ville="Kinshasa", siege=True)
        cls.drh = UniteOrganisationnelle.objects.create(
            code="DRH", nom="Direction RH", type="direction", site=site, date_ouverture=d2015
        )
        cls.closed = UniteOrganisationnelle.objects.create(
            code="DOLD", nom="Ancienne direction", type="direction", site=site,
            date_ouverture=d2015, date_fermeture=date(2019, 1, 1),
        )  # fmt: skip
        cls.chef = Fonction.objects.create(
            code="CS", nom="Chef de service", nature="responsabilite", date_ouverture=d2015
        )
        cat = Categorie.objects.create(code="A", nom="Cadres", rang=3, date_ouverture=d2015)
        grade = Grade.objects.create(
            code="A2", nom="Attaché", categorie=cat, rang=2, date_ouverture=d2015
        )
        cls.e1 = Echelon.objects.create(grade=grade, numero=1, date_ouverture=d2015)
        cls.e2 = Echelon.objects.create(grade=grade, numero=2, date_ouverture=d2015)
        cls.cdi = TypeContrat.objects.create(
            code="CDI", nom="CDI", duree_determinee=False, periode_essai=True,
            date_ouverture=d2015,
        )  # fmt: skip
        cls.agent = Agent.objects.create(
            matricule="ARPTC/0007/2015", nom="Tshibangu", prenom="Didier", sexe="M",
            date_naissance=date(1979, 11, 19), lieu_naissance="Kinshasa",
        )  # fmt: skip
        cls.contrat = Contrat.objects.create(
            agent=cls.agent, type_contrat=cls.cdi, date_debut=date(2020, 3, 1)
        )
        cls.url = f"/admin/agents/agent/{cls.agent.pk}/change/"

    def setUp(self):
        self.client.force_login(self.carriere)

    def affectation(self, jour, unite=None, **extra):
        return {
            "agent": str(self.agent.pk),
            "date_effet": jour,
            "unite": str((unite or self.drh).pk),
            "fonction": str(self.chef.pk),
            **extra,
        }

    def classement(self, jour, echelon=None, **extra):
        return {
            "agent": str(self.agent.pk),
            "date_effet": jour,
            "echelon": str((echelon or self.e1).pk),
            **extra,
        }

    def post(self, affectations=(), classements=(), initial=(0, 0)):
        data = {
            "nom": "Tshibangu",
            "postnom": "",
            "prenom": "Didier",
            "sexe": "M",
            "date_naissance": "1979-11-19",
            "lieu_naissance": "Kinshasa",
            "nationalite": "Congolaise",
            **inline(),
            **contrats(
                {
                    "agent": str(self.agent.pk),
                    "id": str(self.contrat.pk),
                    "type_contrat": str(self.cdi.pk),
                    "date_debut": "2020-03-01",
                    "date_fin": "",
                    "fin_periode_essai": "",
                },
                initial=1,
            ),
            **formset("affectations", *affectations, initial=initial[0]),
            **formset("classements", *classements, initial=initial[1]),
        }
        return self.client.post(self.url, data)

    def formset_of(self, response, prefix):
        return next(
            f.formset
            for f in response.context["inline_admin_formsets"]
            if f.formset.prefix == prefix
        )

    def test_editor_adds_both_and_is_their_author(self):
        response = self.post([self.affectation("2020-03-01")], [self.classement("2020-03-01")])
        self.assertEqual(response.status_code, 302)
        affectation = Affectation.objects.get(agent=self.agent)
        classement = Classement.objects.get(agent=self.agent)
        self.assertEqual((affectation.cree_par, classement.cree_par), (self.carriere,) * 2)
        self.assertEqual(
            set(
                EntreeAudit.objects.filter(
                    action="creation", table__model__in=["affectation", "classement"]
                ).values_list("auteur", "objet_libelle")
            ),
            {
                (self.carriere.pk, "DRH · Chef de service depuis le 01/03/2020 — ARPTC/0007/2015"),
                (self.carriere.pk, "A2 — Échelon 1 depuis le 01/03/2020 — ARPTC/0007/2015"),
            },
        )

    def test_rule_errors_show_next_to_their_field(self):
        response = self.post(
            [self.affectation("2020-03-01", self.closed)], [self.classement("2020-02-29")]
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("unite", self.formset_of(response, "affectations").forms[0].errors)
        self.assertEqual(
            self.formset_of(response, "classements").forms[0].errors["date_effet"],
            [HORS_CONTRAT],
        )
        self.assertFalse(Affectation.objects.exists() or Classement.objects.exists())

    def test_duplicate_date_shows_on_the_row(self):
        existing = Affectation.objects.create(
            agent=self.agent, unite=self.drh, fonction=self.chef, date_effet=date(2020, 3, 1)
        )
        response = self.post(
            [
                self.affectation("2020-03-01", id=str(existing.pk)),
                self.affectation("2020-03-01"),
            ],
            initial=(1, 0),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.formset_of(response, "affectations").forms[1].errors.get("__all__"),
            [AFFECTATION_DATE_PRISE],
        )
        self.assertEqual(Affectation.objects.count(), 1)

    def test_rows_in_date_order_after_the_contracts_one_empty_row_no_delete_box(self):
        later = Classement.objects.create(
            agent=self.agent, echelon=self.e2, date_effet=date(2022, 1, 1)
        )
        earlier = Classement.objects.create(
            agent=self.agent, echelon=self.e1, date_effet=date(2020, 3, 1)
        )
        response = self.client.get(self.url)
        prefixes = [f.formset.prefix for f in response.context["inline_admin_formsets"]]
        self.assertEqual(prefixes[1:], ["contrats", "affectations", "classements"])
        for prefix in ("affectations", "classements"):
            formset = self.formset_of(response, prefix)
            self.assertFalse(formset.can_delete)
            self.assertNotContains(response, f"{prefix}-0-DELETE")
        classements = self.formset_of(response, "classements")
        self.assertEqual([f.instance.pk for f in classements.forms[:2]], [earlier.pk, later.pk])
        self.assertEqual(len(classements.forms), 3)  # two rows and one empty row
        self.assertEqual(len(self.formset_of(response, "affectations").forms), 1)

    def test_add_page_refuses_a_position_without_a_contract(self):
        data = {
            "matricule": "ARPTC/0999/2026",
            "nom": "Tshala",
            "sexe": "F",
            "date_naissance": "1990-06-01",
            "lieu_naissance": "Lubumbashi",
            "nationalite": "Congolaise",
            **inline(),
            **formset("affectations", {**self.affectation("2026-01-05"), "agent": ""}),
        }
        response = self.client.post("/admin/agents/agent/add/", data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.formset_of(response, "affectations").forms[0].errors["date_effet"],
            [HORS_CONTRAT],
        )
        self.assertFalse(Agent.objects.filter(matricule="ARPTC/0999/2026").exists())

    def test_inlines_are_hidden_without_the_permission(self):
        Group.objects.get(name="Gestion de carrière").permissions.remove(
            *Permission.objects.filter(codename__in=["view_affectation", "add_affectation",
                                                     "change_affectation", "view_classement",
                                                     "add_classement", "change_classement"])
        )  # fmt: skip
        response = self.client.get(self.url)
        self.assertNotContains(response, "affectations-TOTAL_FORMS")
        self.assertNotContains(response, "classements-TOTAL_FORMS")


class CompteBancairePermissionTests(TestCase):
    """Bank accounts (bank account D16)."""

    def test_paie_editors_hold_view_add_change_and_nobody_deletes(self):
        self.assertEqual(len(COMPTE_BANCAIRE_EDIT_PERMISSIONS), 3)
        for permission in COMPTE_BANCAIRE_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(holders(permission), PAIE_EDITORS)
        self.assertFalse(Permission.objects.filter(codename="delete_comptebancaire").exists())

    def test_group_setup_regrants_and_keeps_hand_made_ones(self):
        chef = Group.objects.get(name="Chef de service — Rémunération")
        chef.permissions.remove(
            *Permission.objects.filter(codename__in=["add_comptebancaire", "view_agent"])
        )
        direction = Group.objects.get(name="Direction RH")
        direction.permissions.add(Permission.objects.get(codename="view_comptebancaire"))

        sync_groups()

        self.assertEqual(holders("agents.add_comptebancaire"), PAIE_EDITORS)
        self.assertIn("Chef de service — Rémunération", holders("agents.view_agent"))
        self.assertEqual(holders("agents.view_comptebancaire"), PAIE_EDITORS | {"Direction RH"})


class CompteBancaireAdminTests(TestCase):
    COMPTES = "/admin/agents/comptebancaire/"

    @classmethod
    def setUpTestData(cls):
        cls.remuneration = member("remuneration", "Rémunération", is_staff=True)
        cls.chef = member("chef", "Chef de service — Rémunération", is_staff=True)
        cls.bcf = Banque.objects.create(code="BCF", nom="Banque du Fleuve", date_ouverture=D2015)
        cls.bik = Banque.objects.create(code="BIK", nom="Banque de Kinshasa", date_ouverture=D2015)
        cls.closed = Banque.objects.create(
            code="OLD", nom="Ancienne", date_ouverture=D2015, date_fermeture=date(2020, 1, 1)
        )
        cls.kabila = Agent.objects.create(
            matricule="ARPTC/0001/2010", nom="Kabila", sexe="M",
            date_naissance=date(1985, 3, 14), lieu_naissance="Kinshasa",
        )  # fmt: skip
        cls.lumbu = Agent.objects.create(
            matricule="ARPTC/0002/2010", nom="Lumbu", sexe="F",
            date_naissance=date(1988, 5, 2), lieu_naissance="Matadi",
        )  # fmt: skip
        cls.compte = CompteBancaire.objects.create(
            agent=cls.kabila, banque=cls.bcf, numero="05100 0001234", date_effet=date(2021, 3, 1)
        )

    def setUp(self):
        self.client.force_login(self.remuneration)

    def add(self, agent=None, banque=None, numero="05100 0005678", jour="2022-01-01"):
        return self.client.post(f"{self.COMPTES}add/", {
            "agent": (agent or self.lumbu).pk, "banque": (banque or self.bcf).pk,
            "numero": numero, "date_effet": jour,
        })  # fmt: skip

    def errors(self, response):
        self.assertEqual(response.status_code, 200)
        return response.context["adminform"].form.errors

    def test_list_search_and_filter(self):
        page = self.client.get(self.COMPTES)
        self.assertContains(page, "ARPTC/0001/2010")
        self.assertContains(page, "05100 0001234")
        for query in ("q=0001%2F2010", "q=kabila", "q=0001234", f"banque__id__exact={self.bcf.pk}"):
            with self.subTest(query):
                self.assertContains(self.client.get(f"{self.COMPTES}?{query}"), "05100 0001234")
        self.assertNotContains(
            self.client.get(f"{self.COMPTES}?banque__id__exact={self.bik.pk}"), "05100 0001234"
        )

    def test_agent_is_picked_by_autocomplete(self):
        url = (
            "/admin/autocomplete/?app_label=agents&model_name=comptebancaire"
            "&field_name=agent&term=lumbu"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["text"] for r in response.json()["results"]],
                         ["ARPTC/0002/2010 — Lumbu"])  # fmt: skip

    def test_editors_add_an_account_and_are_its_author(self):
        for user, jour in ((self.remuneration, "2022-01-01"), (self.chef, "2023-01-01")):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.add(numero=f" ab{jour[:4]} ", jour=jour).status_code, 302)
                row = CompteBancaire.objects.get(agent=self.lumbu, date_effet=jour)
                self.assertEqual((row.numero, row.cree_par), (f"AB{jour[:4]}", user))
                entry = EntreeAudit.objects.get(table__model="comptebancaire", objet_id=row.pk)
                self.assertEqual((entry.auteur, entry.module), (user, "paie"))

    def test_rule_errors_show_next_to_their_field(self):
        closed = "La banque « OLD » n'est pas ouverte le 01/01/2022."
        cases = [
            ("numero", self.add(numero="1234"), [NUMERO_HELP]),
            ("numero", self.add(numero="05100 0001234"), [NUMERO_PRIS]),
            ("banque", self.add(banque=self.closed), [closed]),
        ]
        for field, response, messages in cases:
            with self.subTest(messages[0]):
                errors = self.errors(response)
                self.assertEqual(errors[field], messages)
                self.assertNotIn("__all__", errors)
        errors = self.errors(self.add(agent=self.kabila, numero="999999", jour="2021-03-01"))
        self.assertEqual(errors["__all__"], [COMPTE_DATE_PRISE])
        self.assertEqual(CompteBancaire.objects.count(), 1)

    def test_correction_keeps_the_agent_and_is_stamped(self):
        url = f"{self.COMPTES}{self.compte.pk}/change/"
        self.assertNotIn('name="agent"', self.client.get(url).content.decode())
        response = self.client.post(url, {
            "agent": self.lumbu.pk, "banque": self.bik.pk, "numero": "05100 0009999",
            "date_effet": "2021-03-01",
        })  # fmt: skip
        self.assertEqual(response.status_code, 302)
        self.compte.refresh_from_db()
        self.assertEqual(
            (self.compte.agent, self.compte.banque, self.compte.numero, self.compte.modifie_par),
            (self.kabila, self.bik, "05100 0009999", self.remuneration),
        )

    def test_nobody_can_delete_not_even_a_superuser(self):
        superuser = get_user_model().objects.create_superuser("root", password="x")
        for user in (self.remuneration, superuser):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                url = f"{self.COMPTES}{self.compte.pk}/delete/"
                self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 403)
                self.assertNotContains(self.client.get(self.COMPTES), "delete_selected")
        self.assertTrue(CompteBancaire.objects.filter(pk=self.compte.pk).exists())

    def test_other_profiles_cannot_open_the_page(self):
        for name in ("Gestion de carrière", "Auditeur", "Administrateur système", "Direction RH"):
            with self.subTest(name):
                self.client.force_login(member(name.split()[0].lower(), name, is_staff=True))
                self.assertEqual(self.client.get(self.COMPTES).status_code, 403)
                self.assertNotContains(self.client.get("/admin/"), "Comptes bancaires")


DOCUMENT_EDITORS = EDITORS | {
    "Administration du personnel",
    "Chef de service — Administration du personnel",
}


class DocumentPermissionTests(TestCase):
    """Scanned documents (document storage D15)."""

    def test_editors_hold_view_add_change_and_nobody_deletes(self):
        self.assertEqual(len(AGENT_DOCUMENT_EDIT_PERMISSIONS), 3)
        for permission in AGENT_DOCUMENT_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(holders(permission), DOCUMENT_EDITORS)
        self.assertFalse(Permission.objects.filter(codename="delete_document").exists())

    def test_group_setup_regrants_and_keeps_hand_made_ones(self):
        chef = Group.objects.get(name="Chef de service — Administration du personnel")
        chef.permissions.remove(Permission.objects.get(codename="add_document"))
        direction = Group.objects.get(name="Direction RH")
        direction.permissions.add(Permission.objects.get(codename="view_document"))

        sync_groups()

        self.assertEqual(holders("agents.add_document"), DOCUMENT_EDITORS)
        self.assertEqual(holders("agents.view_document"), DOCUMENT_EDITORS | {"Direction RH"})


class DocumentAdminTests(TestCase):
    DOCUMENTS = "/admin/agents/document/"

    @classmethod
    def setUpTestData(cls):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.referentiels.models import Cle, Parametre, TypeDocument

        from .documents import create_document

        Parametre.objects.create(cle=Cle.TAILLE_MAX_PIECE, valeur=10, date_ouverture=D2015)
        cls.carriere = member("carriere", "Gestion de carrière", is_staff=True)
        cls.social = member("social", "Social", "Chef de service — Administration du personnel",
                            is_staff=True)  # fmt: skip
        ctr = TypeDocument.objects.create(code="CTR", nom="Contrat signé", date_ouverture=D2015)
        cmd = TypeDocument.objects.create(
            code="CMD", nom="Certificat médical", date_ouverture=D2015, confidentiel=True
        )
        cmd.groupes_autorises.set([Group.objects.get(name="Social")])
        cls.agent = Agent.objects.create(
            matricule="ARPTC/0001/2010", nom="Kabila", sexe="M",
            date_naissance=date(1985, 3, 14), lieu_naissance="Kinshasa",
        )  # fmt: skip
        pdf = b"%PDF-1.4 demo"
        cls.contrat = create_document(cls.agent, ctr, SimpleUploadedFile("contrat.pdf", pdf))
        cls.certificat = create_document(
            cls.agent, cmd, SimpleUploadedFile("certificat-medical.pdf", pdf + b" cmd")
        )

    def test_list_hides_confidential_documents_from_non_members(self):
        self.client.force_login(self.carriere)
        page = self.client.get(self.DOCUMENTS)
        self.assertContains(page, "contrat.pdf")
        self.assertNotContains(page, "certificat-medical.pdf")
        self.client.force_login(self.social)
        page = self.client.get(self.DOCUMENTS)
        self.assertContains(page, "certificat-medical.pdf")

    def test_read_only_no_add_no_delete(self):
        self.client.force_login(self.carriere)
        self.assertEqual(self.client.get(f"{self.DOCUMENTS}add/").status_code, 403)
        page = self.client.get(f"{self.DOCUMENTS}{self.contrat.pk}/change/")
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'name="_save"')
        self.assertNotContains(page, "deletelink")
        self.assertEqual(
            self.client.get(f"{self.DOCUMENTS}{self.certificat.pk}/change/").status_code, 302
        )

    def test_other_profiles_cannot_open_the_page(self):
        formation = member("formation", "Formation", is_staff=True)
        self.client.force_login(formation)
        self.assertEqual(self.client.get(self.DOCUMENTS).status_code, 403)


class PieceJointePermissionTests(TestCase):
    """Links between documents and events (documents on events D20)."""

    def test_editors_hold_view_add_change_and_nobody_deletes(self):
        self.assertEqual(len(PIECE_JOINTE_EDIT_PERMISSIONS), 3)
        for permission in PIECE_JOINTE_EDIT_PERMISSIONS:
            with self.subTest(permission):
                self.assertEqual(holders(permission), DOCUMENT_EDITORS)
        self.assertFalse(Permission.objects.filter(codename="delete_piecejointe").exists())

    def test_group_setup_regrants_and_keeps_hand_made_ones(self):
        chef = Group.objects.get(name="Chef de service — Gestion de carrière")
        chef.permissions.remove(Permission.objects.get(codename="add_piecejointe"))
        direction = Group.objects.get(name="Direction RH")
        direction.permissions.add(Permission.objects.get(codename="view_piecejointe"))

        sync_groups()

        self.assertEqual(holders("agents.add_piecejointe"), DOCUMENT_EDITORS)
        self.assertEqual(holders("agents.view_piecejointe"), DOCUMENT_EDITORS | {"Direction RH"})
