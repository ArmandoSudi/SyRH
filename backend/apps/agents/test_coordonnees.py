"""Contact details. See specs/2026-11-21-contact-details."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, transaction
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import AGENT_FIXED, PHONE_HELP, URGENCE_PAIR, Agent, Coordonnees


def agent(matricule="ARPTC/0001/2010", nom="Mukendi", **values):
    values = {"sexe": "M", "date_naissance": date(1985, 3, 14), "lieu_naissance": "Kinshasa",
              **values}  # fmt: skip
    return Agent.objects.create(matricule=matricule, nom=nom, **values)


def coordonnees(agent, **values):
    values = {"adresse": "Avenue de la Justice 12", "ville": "Kinshasa",
              "telephone": "+243 81 234 5678", **values}  # fmt: skip
    return Coordonnees.objects.create(agent=agent, **values)


def raw(agent, **values):
    """Bypass the model, so only the database decides."""
    values = {"adresse": "Avenue de la Justice 12", "ville": "Kinshasa",
              "telephone": "+243 81 234 5678", **values}  # fmt: skip
    with transaction.atomic():
        Coordonnees._base_manager.bulk_create([Coordonnees(agent=agent, **values)])


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


BAD_PHONES = ("08A1234567", "0812-345-678", "++243812345678", "243+812345678", "0812345",
              "0" * 21, " ")  # fmt: skip
GOOD_PHONES = ("0812345678", "+243 81 234 5678", "+243812345678", "12345678", "0" * 20)


class CoordonneesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.agent = agent(postnom="Kalonji", prenom="Patrick")

    def test_created_with_its_label_and_reachable_from_the_agent(self):
        row = coordonnees(self.agent)
        self.assertEqual(str(row), "Coordonnées de ARPTC/0001/2010 — Mukendi Kalonji Patrick")
        self.assertEqual(Agent.objects.get(pk=self.agent.pk).coordonnees, row)

    def test_agent_without_contact_details_is_valid(self):
        self.agent.full_clean()
        self.assertFalse(Coordonnees.objects.filter(agent=self.agent).exists())

    def test_required_and_optional_fields(self):
        self.assertEqual(
            set(errors_of(Coordonnees().full_clean)), {"agent", "adresse", "ville", "telephone"}
        )
        Coordonnees(agent=self.agent, adresse="Av. 1", ville="Goma",
                    telephone="0812345678").full_clean()  # fmt: skip

    def test_text_phones_and_email_are_normalised(self):
        row = coordonnees(self.agent, adresse="  Av. du Port 3 ", commune=" Gombe ",
                          ville=" Kinshasa ", telephone=" +243  81 234   5678 ",
                          telephone_secondaire=" 0991234567 ", courriel=" Agent@Example.CD ",
                          urgence_nom=" Nsimba Lukau ", urgence_lien=" Épouse ",
                          urgence_telephone="0 812 345 679")  # fmt: skip
        row.refresh_from_db()
        self.assertEqual(
            (row.adresse, row.commune, row.ville, row.telephone, row.telephone_secondaire,
             row.courriel, row.urgence_nom, row.urgence_lien, row.urgence_telephone),
            ("Av. du Port 3", "Gombe", "Kinshasa", "+243 81 234 5678", "0991234567",
             "agent@example.cd", "Nsimba Lukau", "Épouse", "0 812 345 679"),
        )  # fmt: skip

    def test_bad_phone_is_reported_on_its_field(self):
        for field in ("telephone", "telephone_secondaire"):
            for phone in BAD_PHONES[:-1]:
                with self.subTest(field=field, phone=phone):
                    values = {"telephone": "0812345678", field: phone}
                    row = Coordonnees(agent=self.agent, adresse="Av. 1", ville="Goma", **values)
                    errors = errors_of(row.full_clean)
                    self.assertIn(PHONE_HELP, errors[field])
                    self.assertNotIn("__all__", errors)
        with self.assertRaises(ValidationError):
            coordonnees(self.agent, telephone="08A1234567")

    def test_good_phones_are_accepted(self):
        for phone in GOOD_PHONES:
            with self.subTest(phone=phone):
                Coordonnees(agent=self.agent, adresse="Av. 1", ville="Goma",
                            telephone=phone).full_clean()  # fmt: skip

    def test_bad_email_is_reported_and_two_agents_may_share_one(self):
        row = Coordonnees(agent=self.agent, adresse="Av. 1", ville="Goma",
                          telephone="0812345678", courriel="pas-une-adresse")  # fmt: skip
        self.assertIn("courriel", errors_of(row.full_clean))
        coordonnees(self.agent, courriel="famille@example.cd")
        coordonnees(agent("ARPTC/0002/2010", "Nsimba"), courriel="famille@example.cd")

    def test_emergency_name_and_phone_go_together(self):
        def check(**values):
            row = Coordonnees(agent=self.agent, adresse="Av. 1", ville="Goma",
                              telephone="0812345678", **values)  # fmt: skip
            return errors_of(row.full_clean)

        self.assertEqual(check(urgence_nom="Nsimba"), {"urgence_telephone": [URGENCE_PAIR]})
        self.assertEqual(check(urgence_telephone="0812345679"), {"urgence_nom": [URGENCE_PAIR]})
        self.assertIn(PHONE_HELP, check(urgence_nom="Nsimba", urgence_telephone="abc")[
            "urgence_telephone"])  # fmt: skip
        for values in ({}, {"urgence_nom": "Nsimba", "urgence_telephone": "0812345679"},
                       {"urgence_nom": "Nsimba", "urgence_lien": "Épouse",
                        "urgence_telephone": "0812345679"}):  # fmt: skip
            with self.subTest(values=values):
                Coordonnees(agent=self.agent, adresse="Av. 1", ville="Goma",
                            telephone="0812345678", **values).full_clean()  # fmt: skip
        with self.assertRaises(ValidationError):
            coordonnees(self.agent, urgence_nom="Nsimba")

    def test_agent_is_fixed_but_values_can_be_corrected(self):
        row = coordonnees(self.agent)
        row.telephone = "0991234567"
        row.full_clean()
        row.save()

        row.agent = agent("ARPTC/0002/2010", "Nsimba")
        self.assertEqual(errors_of(row.full_clean)["agent"], [AGENT_FIXED])
        with self.assertRaises(ValidationError):
            row.save()
        row.refresh_from_db()
        self.assertEqual((row.agent_id, row.telephone), (self.agent.pk, "0991234567"))

    def test_never_deleted(self):
        row = coordonnees(self.agent)
        with self.assertRaises(PermissionError):
            row.delete()
        self.assertTrue(Coordonnees.objects.filter(pk=row.pk).exists())
        self.assertEqual(Coordonnees._meta.default_permissions, ("view", "add", "change"))


class CoordonneesConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D11)."""

    @classmethod
    def setUpTestData(cls):
        cls.agent = agent()

    def test_valid_rows_are_accepted(self):
        raw(self.agent, commune="Gombe", telephone_secondaire="0991234567",
            courriel="a@example.cd", urgence_nom="Nsimba",
            urgence_telephone="0812345679")  # fmt: skip
        raw(agent("ARPTC/0002/2010", "Nsimba"))
        self.assertEqual(Coordonnees.objects.count(), 2)

    def test_second_row_for_one_agent_is_refused(self):
        raw(self.agent)
        with self.assertRaises(IntegrityError):
            raw(self.agent, telephone="0991234567")

    def test_blank_address_town_or_phone_is_refused(self):
        for values in ({"adresse": ""}, {"adresse": "  "}, {"ville": ""}, {"telephone": ""}):
            with self.subTest(values=values), self.assertRaises(IntegrityError):
                raw(self.agent, **values)

    def test_bad_phones_are_refused(self):
        for field in ("telephone", "telephone_secondaire"):
            for phone in BAD_PHONES:
                # 21 characters overflow the column (DataError) before the check runs.
                refused = (IntegrityError, DataError)
                with self.subTest(field=field, phone=phone), self.assertRaises(refused):
                    raw(self.agent, **{field: phone})

    def test_good_phones_are_accepted(self):
        for index, phone in enumerate(GOOD_PHONES):
            raw(agent(f"P/{index}", "Phone"), telephone=phone, telephone_secondaire=phone)

    def test_lone_emergency_name_or_phone_is_refused(self):
        for values in ({"urgence_nom": "Nsimba"}, {"urgence_telephone": "0812345679"},
                       {"urgence_nom": " ", "urgence_telephone": "0812345679"},
                       {"urgence_nom": "Nsimba", "urgence_telephone": "abc"}):  # fmt: skip
            with self.subTest(values=values), self.assertRaises(IntegrityError):
                raw(self.agent, **values)


class CoordonneesAuditTests(TestCase):
    def test_create_and_correct_are_audited_with_label_and_author(self):
        user = get_user_model().objects.create_user("carriere", password="x")
        row = coordonnees(agent(), cree_par=user, modifie_par=user)
        row.telephone = "0991234567"
        row.save()

        entries = EntreeAudit.objects.filter(table__model="coordonnees", objet_id=row.pk)
        self.assertEqual(
            set(entries.values_list("action", "module", "objet_libelle", "auteur")),
            {
                ("creation", "agents", "Coordonnées de ARPTC/0001/2010 — Mukendi", user.pk),
                ("modification", "agents", "Coordonnées de ARPTC/0001/2010 — Mukendi", user.pk),
            },
        )
