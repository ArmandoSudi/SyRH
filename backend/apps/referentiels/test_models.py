from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.audit.models import EntreeAudit

from .models import Site, UniteOrganisationnelle

T = UniteOrganisationnelle.Type
Unite = UniteOrganisationnelle
D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
D2025 = date(2025, 7, 1)


def site(code="KIN", **extra):
    values = {"nom": f"Site {code}", "ville": "Kinshasa", **extra}
    return Site.objects.create(code=code, **values)


def unite(code, type_, parent=None, *, at=None, debut=D2015, fin=None, nom=None):
    return Unite.objects.create(
        code=code,
        nom=nom or f"Unité {code}",
        type=type_,
        parent=parent,
        site=at or (parent.site if parent else Site.objects.get(code="KIN")),
        date_ouverture=debut,
        date_fermeture=fin,
    )


def raw(**values):
    """Bypass the model rules, so only the database decides."""
    obj = Unite(**values)
    with transaction.atomic():
        Unite._base_manager.bulk_create([obj])


def errors_of(call) -> dict[str, list[str]]:
    try:
        call()
    except ValidationError as error:
        return error.message_dict
    raise AssertionError("no ValidationError")


class SiteTests(TestCase):
    def test_site_is_created_and_audited(self):
        kin = site("kin", siege=True)

        self.assertEqual(kin.code, "KIN")
        self.assertEqual(str(kin), "KIN — Site kin")
        entry = EntreeAudit.objects.get(objet_id=kin.pk, table__model="site")
        self.assertEqual((entry.module, entry.objet_libelle), ("referentiels", "KIN — Site kin"))

    def test_one_open_head_office(self):
        site("KIN", siege=True)
        site("OLD", siege=True, date_fermeture=D2015)  # a closed head office is history

        with self.assertRaises(IntegrityError), transaction.atomic():
            site("LUB", siege=True)

        lub = Site(code="LUB", nom="Lubumbashi", ville="Lubumbashi", siege=True)
        self.assertIn("Un autre site ouvert est déjà le siège.", str(errors_of(lub.full_clean)))

    def test_code_is_unique(self):
        site("KIN")

        with self.assertRaises(IntegrityError), transaction.atomic():
            site("KIN")

    def test_no_delete_permission(self):
        for model in (Site, Unite):
            with self.subTest(model.__name__):
                self.assertEqual(model._meta.default_permissions, ("view", "add", "change"))

    def test_cannot_close_with_an_open_unit(self):
        lub = site("LUB")
        unite("RP", T.DIRECTION, at=lub, fin=D2025)
        unite("RP2", T.DIRECTION, at=lub)

        lub.date_fermeture = D2025
        self.assertIn("RP2", errors_of(lub.save)["date_fermeture"][0])

        rp2 = Unite.objects.get(code="RP2")
        rp2.date_fermeture = D2025
        rp2.save()
        lub.save()  # every unit closes by then


class ConstraintTests(TestCase):
    """Rules on the row itself, enforced by PostgreSQL (D13)."""

    @classmethod
    def setUpTestData(cls):
        cls.kin = site("KIN", siege=True)
        cls.dg = unite("DG", T.DIRECTION)

    def assert_refused(self, **values):
        values = {"nom": "x", "site": self.kin, "date_ouverture": D2015, **values}
        with self.assertRaises(IntegrityError):
            raw(**values)

    def test_direction_if_and_only_if_root(self):
        self.assert_refused(code="X1", type=T.DIRECTION, parent=self.dg)
        self.assert_refused(code="X2", type=T.SERVICE, parent=None)
        raw(
            code="OK1", nom="x", site=self.kin, date_ouverture=D2015, type=T.SERVICE, parent=self.dg
        )

    def test_not_its_own_parent(self):
        service = unite("SRV", T.SERVICE, self.dg)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Unite._base_manager.filter(pk=service.pk).update(parent=service.pk)

    def test_closing_after_opening(self):
        self.assert_refused(code="X3", type=T.DIRECTION, date_fermeture=D2015)
        self.assert_refused(code="X4", type=T.DIRECTION, date_fermeture=date(2014, 1, 1))

    def test_code_unique_over_overlapping_periods(self):
        self.assert_refused(code="DG", type=T.DIRECTION, date_ouverture=D2020)
        unite("OLD", T.DIRECTION, fin=D2020)
        # Consecutive periods may share a code: the closing day is the first day closed.
        raw(code="OLD", nom="x", site=self.kin, type=T.DIRECTION, date_ouverture=D2020)
        self.assert_refused(code="OLD", type=T.DIRECTION, date_ouverture=date(2019, 12, 31))

    def test_constraints_have_french_messages_in_forms(self):
        twin = Unite(code="dg", nom="Bis", type=T.DIRECTION, site=self.kin, date_ouverture=D2020)
        self.assertIn("porte déjà ce code", str(errors_of(twin.full_clean)))

        orphan = Unite(code="S", nom="S", type=T.SERVICE, site=self.kin, date_ouverture=D2020)
        self.assertIn("Une direction n'a pas d'unité parente", str(errors_of(orphan.full_clean)))

    def test_referenced_rows_are_protected(self):
        unite("SRV", T.SERVICE, self.dg)

        with self.assertRaises(ProtectedError), transaction.atomic():
            self.dg.delete()
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.kin.delete()


class RuleTests(TestCase):
    """Rules that read other rows, checked by clean() and by save() (D14)."""

    @classmethod
    def setUpTestData(cls):
        cls.kin = site("KIN", siege=True)
        cls.drh = unite("DRH", T.DIRECTION)
        cls.dep = unite("DRH-DEP", T.DEPARTEMENT, cls.drh)
        cls.srv = unite("DRH-SRV", T.SERVICE, cls.dep)

    def check_both(self, obj, field, fragment):
        """The same error from full_clean() (forms) and from save() (scripts)."""
        for call in (obj.full_clean, obj.save):
            with self.subTest(call.__name__):
                messages = errors_of(call)
                self.assertIn(field, messages)
                self.assertIn(fragment, " ".join(messages[field]))

    def new(self, code, type_, parent, **extra):
        values = {"nom": code, "site": self.kin, "date_ouverture": D2020, **extra}
        return Unite(code=code, type=type_, parent=parent, **values)

    def test_codes_are_saved_in_capitals(self):
        self.assertEqual(unite("drh-xyz", T.SERVICE, self.drh).code, "DRH-XYZ")

    def test_parent_must_be_of_a_higher_level(self):
        self.check_both(
            self.new("B1", T.DEPARTEMENT, self.dep),
            "parent",
            "Un département ne peut pas relever d'un département",
        )
        self.check_both(self.new("B2", T.DEPARTEMENT, self.srv), "parent", "d'un service")

    def test_levels_may_be_skipped(self):
        unite("B3", T.SERVICE, self.drh)
        unite("B4", T.BUREAU, self.dep)
        unite("B5", T.BUREAU, self.drh)

    def test_type_parent_and_site_never_change(self):
        lub = site("LUB")
        other = unite("DT", T.DIRECTION)
        changes = {"type": T.BUREAU, "parent": other, "site": lub}
        for field, value in changes.items():
            with self.subTest(field):
                srv = Unite.objects.get(pk=self.srv.pk)
                setattr(srv, field, value)
                self.check_both(srv, field, "fermez l'unité et ouvrez-en une nouvelle")

    def test_code_name_and_dates_can_be_corrected(self):
        srv = Unite.objects.get(pk=self.srv.pk)
        srv.code, srv.nom, srv.date_ouverture = "DRH-SRV2", "Service corrigé", D2020
        srv.full_clean()
        srv.save()

    def test_cannot_open_before_its_parent(self):
        late = unite("LATE", T.DIRECTION, debut=D2020)
        self.check_both(
            self.new("B6", T.SERVICE, late, date_ouverture=D2015),
            "date_ouverture",
            "avant son unité parente (01/01/2020)",
        )

    def test_cannot_stay_open_after_its_parent(self):
        short = unite("SHORT", T.DIRECTION, fin=D2025)
        message = "au plus tard à la fermeture de son unité parente (01/07/2025)"
        self.check_both(self.new("B7", T.SERVICE, short), "date_fermeture", message)
        self.check_both(
            self.new("B8", T.SERVICE, short, date_fermeture=date(2026, 1, 1)),
            "date_fermeture",
            message,
        )
        unite("B9", T.SERVICE, short, debut=D2020, fin=D2025)

    def test_parent_cannot_close_before_its_children(self):
        dep = Unite.objects.get(pk=self.dep.pk)
        dep.date_fermeture = D2025
        self.check_both(dep, "date_fermeture", "DRH-SRV")

        srv = Unite.objects.get(pk=self.srv.pk)
        srv.date_fermeture = D2025
        srv.save()
        dep.save()

    def test_parent_cannot_open_after_its_children(self):
        dep = Unite.objects.get(pk=self.dep.pk)
        dep.date_ouverture = D2020
        self.check_both(dep, "date_ouverture", "DRH-SRV")

    def test_unit_must_close_by_its_site_closing(self):
        lub = site("LUB", date_fermeture=D2025)
        self.check_both(self.new("RP", T.DIRECTION, None, site=lub), "site", "01/07/2025")
        unite("RP", T.DIRECTION, at=lub, fin=D2025)


class HistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.kin = site("KIN", siege=True)
        cls.dt = unite("DT", T.DIRECTION)
        cls.tel = unite("DT-TEL", T.DEPARTEMENT, cls.dt)
        cls.old = unite("DT-CTL", T.SERVICE, cls.tel, fin=D2025, nom="Service Contrôle")

    def codes_on(self, day):
        return set(Unite.objects.ouvertes(day).values_list("code", "nom"))

    def test_open_from_opening_day_to_closing_day_excluded(self):
        before, on, after = date(2014, 12, 31), D2015, date(2025, 6, 30)

        self.assertNotIn(("DT", "Unité DT"), self.codes_on(before))
        self.assertIn(("DT", "Unité DT"), self.codes_on(on))
        self.assertIn(("DT-CTL", "Service Contrôle"), self.codes_on(after))
        self.assertNotIn(("DT-CTL", "Service Contrôle"), self.codes_on(D2025))

    def test_restructuring_keeps_the_old_tree(self):
        new = unite("DT-CTL", T.DEPARTEMENT, self.dt, debut=D2025, nom="Département Contrôle")

        self.assertIn(("DT-CTL", "Service Contrôle"), self.codes_on(date(2025, 6, 30)))
        self.assertNotIn(("DT-CTL", "Département Contrôle"), self.codes_on(date(2025, 6, 30)))
        self.assertIn(("DT-CTL", "Département Contrôle"), self.codes_on(D2025))
        self.assertEqual(Unite.objects.get(pk=self.old.pk).parent, self.tel)
        self.assertEqual(new.parent, self.dt)

    def test_create_rename_and_close_are_audited(self):
        srv = unite("DT-NEW", T.SERVICE, self.tel)
        srv.nom = "Service renommé"
        srv.save()
        srv.date_fermeture = D2025
        srv.save()

        entries = EntreeAudit.objects.filter(table__model="uniteorganisationnelle", objet_id=srv.pk)
        self.assertEqual(
            [e.action for e in entries.order_by("id")],
            ["creation", "modification", "modification"],
        )
        rename = entries.order_by("id")[1]
        self.assertEqual(rename.objet_libelle, "DT-NEW — Service renommé")
        self.assertEqual(rename.module, "referentiels")
        self.assertEqual(
            rename.changements,
            [
                {
                    "champ": "nom",
                    "libelle": "nom",
                    "avant": "Unité DT-NEW",
                    "apres": "Service renommé",
                }
            ],
        )


class ReversedDatesTests(TestCase):
    """A closing date before the opening date is a message, not a database error."""

    def test_unit_reports_the_closing_date(self):
        obj = UniteOrganisationnelle(
            code="DG", nom="Direction générale", type=T.DIRECTION,
            date_ouverture=D2020, date_fermeture=D2015,
        )  # fmt: skip
        errors = errors_of(obj.full_clean)
        self.assertEqual(
            errors["date_fermeture"],
            ["La date de fermeture doit être postérieure à la date d'ouverture."],
        )
        self.assertNotIn("__all__", errors)
