"""Who edits agents, their contact details and contracts, and the Django admin (agent
identity D14 to D16, contact details D15, D16, contract D16, D17)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.accounts.roles import (
    AGENT_EDIT_PERMISSIONS,
    CONTRAT_EDIT_PERMISSIONS,
    COORDONNEES_EDIT_PERMISSIONS,
    sync_groups,
)
from apps.audit.models import EntreeAudit
from apps.referentiels.models import TypeContrat

from .models import (
    CONTRAT_OVERLAP,
    ESSAI_INTERDIT,
    FIN_OBLIGATOIRE,
    MATRICULE_TAKEN,
    PHONE_HELP,
    URGENCE_PAIR,
    Agent,
    Contrat,
    Coordonnees,
)

EDITORS = {"Gestion de carrière", "Chef de service — Gestion de carrière"}


def inline(initial=0, **row):
    """The contact details inline of the agent page: empty, or one row (D16)."""
    data = {
        "coordonnees-TOTAL_FORMS": "1" if row or initial else "0",
        "coordonnees-INITIAL_FORMS": str(initial),
        "coordonnees-MIN_NUM_FORMS": "0",
        "coordonnees-MAX_NUM_FORMS": "1",
    }
    data.update({f"coordonnees-0-{name}": value for name, value in row.items()})
    return {**data, **contrats()}


def contrats(*rows, initial=0):
    """The contracts inline of the agent page: its management fields and rows (contract
    D17). The first `initial` rows are existing contracts, carrying their id."""
    data = {
        "contrats-TOTAL_FORMS": str(len(rows)),
        "contrats-INITIAL_FORMS": str(initial),
        "contrats-MIN_NUM_FORMS": "0",
        "contrats-MAX_NUM_FORMS": "1000",
    }
    for index, row in enumerate(rows):
        data.update({f"contrats-{index}-{name}": value for name, value in row.items()})
    return data


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
        for user in (self.remuneration, self.admin):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.AGENTS).status_code, 403)
                self.assertEqual(self.client.get(f"{self.AGENTS}add/").status_code, 403)


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
