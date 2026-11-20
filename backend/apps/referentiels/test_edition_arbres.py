"""Editing the tree reference tables through the API.

See specs/2026-11-20-tree-reference-screens.
"""

from datetime import date

from django.db import connection

from apps.audit.models import EntreeAudit

from .models import (
    Categorie,
    Echelon,
    Grade,
    MotifSortie,
    PieceRequise,
    Site,
    TypeDocument,
    TypeSuspension,
    UniteOrganisationnelle,
)
from .test_edition import EditionTestCase

D2015 = date(2015, 1, 1)
D2020 = date(2020, 1, 1)
API = "/api/referentiels/"
T = UniteOrganisationnelle.Type


class TreeFixtures(EditionTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.kin = Site.objects.create(code="KIN", nom="Siège", ville="Kinshasa", siege=True)
        cls.lub = Site.objects.create(code="LUB", nom="Lubumbashi", ville="Lubumbashi")
        cls.drh = UniteOrganisationnelle.objects.create(
            code="DRH", nom="Direction RH", type=T.DIRECTION, site=cls.kin, date_ouverture=D2015
        )
        cls.dep = UniteOrganisationnelle.objects.create(
            code="DRH-CAR", nom="Département Carrière", type=T.DEPARTEMENT, parent=cls.drh,
            site=cls.kin, date_ouverture=D2015,
        )  # fmt: skip
        cls.ser = UniteOrganisationnelle.objects.create(
            code="DRH-CAR-PRO", nom="Service Promotions", type=T.SERVICE, parent=cls.dep,
            site=cls.lub, date_ouverture=D2015,
        )  # fmt: skip
        cls.cd = Categorie.objects.create(code="CD", nom="Cadres", rang=3, date_ouverture=D2015)
        cls.am = Categorie.objects.create(code="AM", nom="Maîtrise", rang=2, date_ouverture=D2015)
        cls.a1 = Grade.objects.create(code="A1", nom="Attaché", categorie=cls.cd, rang=1,
                                      date_ouverture=D2015)  # fmt: skip
        cls.e1 = Echelon.objects.create(grade=cls.a1, numero=1, date_ouverture=D2015)
        cls.e2 = Echelon.objects.create(grade=cls.a1, numero=2, date_ouverture=D2015)
        cls.dec = TypeDocument.objects.create(code="DEC", nom="Décision", date_ouverture=D2015)
        cls.ama = TypeDocument.objects.create(code="AMA", nom="Acte de mariage",
                                              date_ouverture=D2015)  # fmt: skip
        cls.promo = PieceRequise.objects.create(evenement="promotion", type_document=cls.dec,
                                                obligatoire=True, date_ouverture=D2015)  # fmt: skip
        cls.ret = MotifSortie.objects.create(code="RET", nom="Retraite", type_document=cls.dec,
                                             retraite=True, date_ouverture=D2015)  # fmt: skip
        cls.deta = TypeSuspension.objects.create(code="DETA", nom="Détachement",
                                                 type_document=cls.dec, compte_anciennete=True,
                                                 date_ouverture=D2015)  # fmt: skip

    def setUp(self):
        self.api = self.client_for(self.carriere)

    def post(self, url, data, user=None):
        return self.client_for(user or self.carriere).post(f"{API}{url}", data, format="json")

    def patch(self, url, data, user=None):
        return self.client_for(user or self.carriere).patch(f"{API}{url}", data, format="json")


class TreeWriteTests(TreeFixtures):
    """Create, correct and the fixed fields on the seven tables (D1 to D3)."""

    def test_sites(self):
        created = self.post("sites/", {"code": "mat", "nom": "Matadi", "ville": "Matadi"})
        self.assertEqual((created.status_code, created.json()["code"]), (201, "MAT"))
        second = self.post("sites/", {"code": "X", "nom": "X", "ville": "X", "siege": True})
        self.assertEqual(second.status_code, 400)
        self.assertIn("déjà le siège", str(second.json()))
        closing = self.patch(f"sites/{self.kin.pk}/", {"date_fermeture": "2020-01-01"})
        self.assertEqual(closing.status_code, 400)
        self.assertIn("Des unités de ce site restent ouvertes", closing.json()["date_fermeture"][0])

    def test_a_site_has_no_successor(self):
        response = self.post(f"sites/{self.lub.pk}/successeur/", {"date_effet": "2020-01-01"})
        self.assertEqual(response.status_code, 405)

    def test_units(self):
        created = self.post("unites/", {"code": "drh-for", "nom": "Département Formation",
                            "type": "departement", "parent": self.drh.pk, "site_id": self.kin.pk,
                            "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(created.status_code, 201)
        self.assertEqual((created.json()["code"], created.json()["site"]["code"]),
                         ("DRH-FOR", "KIN"))  # fmt: skip

        wrong_level = self.post("unites/", {"code": "X", "nom": "X", "type": "direction",
                                "parent": self.dep.pk, "site_id": self.kin.pk,
                                "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(wrong_level.status_code, 400)

        renamed = self.patch(f"unites/{self.ser.pk}/", {"nom": "Service des promotions"})
        self.assertEqual(renamed.status_code, 200)
        for field, value in (("parent", self.drh.pk), ("type", "bureau"), ("site_id", self.kin.pk)):
            with self.subTest(field):
                refused = self.patch(f"unites/{self.ser.pk}/", {field: value})
                self.assertEqual(refused.status_code, 400)
                self.assertIn("Ne peut pas être modifié", str(refused.json()))

    def test_classification(self):
        a2 = {"code": "a2", "nom": "Attaché principal", "categorie": self.cd.pk, "rang": 2}
        grade = self.post("grades/", {**a2, "date_ouverture": "2014-01-01"})
        self.assertEqual(grade.status_code, 400)
        self.assertIn("date_ouverture", grade.json())
        grade = self.post("grades/", {**a2, "date_ouverture": "2015-01-01"})
        self.assertEqual(grade.status_code, 201)
        echelon = self.post("echelons/", {"grade": self.a1.pk, "numero": 3,
                            "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual((echelon.status_code, echelon.json()["libelle"]), (201, "A1 — Échelon 3"))
        moved = self.patch(f"grades/{self.a1.pk}/", {"categorie": self.am.pk})
        self.assertEqual(moved.status_code, 400)
        self.assertIn("categorie", moved.json())
        category = self.post("categories/", {"code": "ex", "nom": "Exécution", "rang": 1,
                             "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(category.status_code, 201)

    def test_documents(self):
        created = self.post("types-document/", {"code": "cni", "nom": "Pièce d'identité",
                            "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(created.status_code, 201)
        piece = self.post("pieces-requises/", {
            "evenement": "mariage", "type_document": self.ama.pk, "obligatoire": True,
            "date_ouverture": "2015-01-01"})  # fmt: skip
        self.assertEqual(piece.status_code, 201)
        duplicate = self.post("pieces-requises/", {
            "evenement": "promotion", "type_document": self.dec.pk, "obligatoire": False,
            "date_ouverture": "2020-01-01"})  # fmt: skip
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("exige déjà", duplicate.json()["non_field_errors"][0])
        fixed = self.patch(f"pieces-requises/{self.promo.pk}/", {"evenement": "mutation"})
        self.assertEqual(fixed.status_code, 400)
        self.assertIn("evenement", fixed.json())
        optional = self.patch(f"pieces-requises/{self.promo.pk}/", {"obligatoire": False})
        self.assertEqual(optional.status_code, 200)

    def test_readers_cannot_write_and_nobody_deletes(self):
        rows = {"sites/": self.lub, "unites/": self.ser, "categories/": self.am,
                "grades/": self.a1, "echelons/": self.e1, "types-document/": self.ama,
                "pieces-requises/": self.promo}  # fmt: skip
        for url, obj in rows.items():
            for user in (self.auditeur, self.remuneration):
                with self.subTest(url=url, user=user.username):
                    self.assertEqual(self.patch(f"{url}{obj.pk}/", {}, user).status_code, 403)
                    self.assertEqual(self.post(url, {}, user).status_code, 403)
            self.assertEqual(
                self.client_for(self.admin).delete(f"{API}{url}{obj.pk}/").status_code, 405
            )
            self.assertEqual(self.patch(f"{url}{obj.pk}/", {}, self.admin).status_code, 200)


class CarryOverTests(TreeFixtures):
    """Replacing a parent at a date carries its open children over (D4 to D10)."""

    def successeur(self, url, pk, **values):
        return self.post(f"{url}{pk}/successeur/", values)

    def test_renaming_a_direction_carries_its_whole_subtree(self):
        bureau = UniteOrganisationnelle.objects.create(
            code="DRH-CAR-PRO-B1", nom="Bureau 1", type=T.BUREAU, parent=self.ser,
            site=self.lub, date_ouverture=D2015,
        )  # fmt: skip
        closed = UniteOrganisationnelle.objects.create(
            code="DRH-OLD", nom="Ancien département", type=T.DEPARTEMENT, parent=self.drh,
            site=self.kin, date_ouverture=D2015, date_fermeture=date(2018, 1, 1),
        )  # fmt: skip

        response = self.successeur("unites/", self.drh.pk, date_effet="2020-01-01",
                                   nom="Direction des ressources humaines")  # fmt: skip
        self.assertEqual(response.status_code, 201)
        new_drh = UniteOrganisationnelle.objects.get(pk=response.json()["id"])

        def tree(day):
            rows = UniteOrganisationnelle.objects.ouvertes(day).select_related("parent", "site")
            return {(u.code, u.nom, u.parent.code if u.parent else None, u.site.code)
                    for u in rows}  # fmt: skip

        self.assertEqual(tree(date(2019, 12, 31)), tree(date(2019, 6, 1)))
        self.assertIn(("DRH", "Direction RH", None, "KIN"), tree(date(2019, 12, 31)))
        self.assertEqual(tree(D2020), {
            ("DRH", "Direction des ressources humaines", None, "KIN"),
            ("DRH-CAR", "Département Carrière", "DRH", "KIN"),
            ("DRH-CAR-PRO", "Service Promotions", "DRH-CAR", "LUB"),
            ("DRH-CAR-PRO-B1", "Bureau 1", "DRH-CAR-PRO", "LUB"),
        })  # fmt: skip
        for old in (self.dep, self.ser, bureau):
            old.refresh_from_db()
            self.assertEqual(old.date_fermeture, D2020)
        new_dep = new_drh.enfants.get()
        self.assertNotEqual(new_dep.pk, self.dep.pk)
        self.assertEqual(new_dep.enfants.get().enfants.get().code, "DRH-CAR-PRO-B1")
        closed.refresh_from_db()
        self.assertEqual(closed.date_fermeture, date(2018, 1, 1))  # not carried, not touched

    def test_every_row_carries_the_author_and_is_audited(self):
        self.successeur("unites/", self.drh.pk, date_effet="2020-01-01", nom="DRH")
        for unit in UniteOrganisationnelle.objects.all():
            self.assertEqual(unit.modifie_par, self.carriere, unit.code)
        entries = EntreeAudit.objects.filter(
            table__model="uniteorganisationnelle", auteur=self.carriere
        )
        created = entries.filter(action="creation")
        changed = entries.filter(action="modification")
        self.assertEqual((created.count(), changed.count()), (3, 3))

    def test_a_category_carries_its_grades_and_their_steps(self):
        response = self.successeur("categories/", self.cd.pk, date_effet="2020-01-01",
                                   nom="Cadres supérieurs")  # fmt: skip
        self.assertEqual(response.status_code, 201)
        grade = Grade.objects.ouvertes(D2020).get(code="A1")
        self.assertEqual(grade.categorie.nom, "Cadres supérieurs")
        self.assertEqual(sorted(grade.echelons.values_list("numero", flat=True)), [1, 2])
        self.assertEqual(Grade.objects.ouvertes(date(2019, 12, 31)).get(code="A1"), self.a1)

    def test_a_grade_carries_its_steps(self):
        response = self.successeur("grades/", self.a1.pk, date_effet="2020-01-01",
                                   nom="Attaché de 1re classe")  # fmt: skip
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Echelon.objects.ouvertes(D2020).filter(grade__nom__startswith="Attaché de")
                         .count(), 2)  # fmt: skip

    def test_a_document_type_carries_requirements_reasons_and_suspensions(self):
        response = self.successeur("types-document/", self.dec.pk, date_effet="2020-01-01",
                                   nom="Décision de l'autorité")  # fmt: skip
        self.assertEqual(response.status_code, 201)
        new = TypeDocument.objects.get(pk=response.json()["id"])
        self.assertEqual(PieceRequise.objects.ouvertes(D2020).get(evenement="promotion")
                         .type_document, new)  # fmt: skip
        self.assertEqual(MotifSortie.objects.ouvertes(D2020).get(code="RET").type_document, new)
        self.assertEqual(TypeSuspension.objects.ouvertes(D2020).get(code="DETA").type_document,
                         new)  # fmt: skip
        self.assertEqual(MotifSortie.objects.ouvertes(date(2019, 1, 1)).get().type_document,
                         self.dec)  # fmt: skip

    def test_a_refused_copy_cancels_everything(self):
        with connection.cursor() as cursor:  # bypass the model, which would refuse it
            cursor.execute(
                "UPDATE referentiels_site SET date_fermeture = %s WHERE id = %s",
                [date(2021, 1, 1), self.lub.pk],
            )
        before = UniteOrganisationnelle.objects.count()
        # The service sits on a site that closes in 2021: its copy from 2022 is refused.
        response = self.successeur("unites/", self.drh.pk, date_effet="2022-01-01", nom="DRH")
        self.assertEqual(response.status_code, 400)
        message = response.json()["non_field_errors"][0]
        self.assertIn("DRH-CAR-PRO", message)
        self.assertEqual(UniteOrganisationnelle.objects.count(), before)
        for unit in (self.drh, self.dep, self.ser):
            unit.refresh_from_db()
            self.assertIsNone(unit.date_fermeture)

    def test_a_child_opening_on_or_after_the_date_blocks_and_is_named(self):
        UniteOrganisationnelle.objects.create(
            code="DRH-NEW", nom="Nouveau département", type=T.DEPARTEMENT, parent=self.drh,
            site=self.kin, date_ouverture=date(2021, 1, 1),
        )  # fmt: skip
        response = self.successeur("unites/", self.drh.pk, date_effet="2020-01-01", nom="DRH")
        self.assertEqual(response.status_code, 400)
        self.assertIn("DRH-NEW", response.json()["date_effet"][0])
        preview = self.client_for(self.carriere).get(
            f"{API}unites/{self.drh.pk}/suite/", {"date_effet": "2020-01-01"}
        )
        self.assertEqual(len(preview.json()["bloquants"]), 1)
        self.drh.refresh_from_db()
        self.assertIsNone(self.drh.date_fermeture)

    def test_closing_a_parent_or_a_site_with_open_children_stays_refused(self):
        response = self.patch(f"unites/{self.drh.pk}/", {"date_fermeture": "2020-01-01"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("DRH-CAR", str(response.json()))
        response = self.patch(f"categories/{self.cd.pk}/", {"date_fermeture": "2020-01-01"})
        self.assertEqual(response.status_code, 400)
        response = self.patch(f"sites/{self.lub.pk}/", {"date_fermeture": "2020-01-01"})
        self.assertEqual(response.status_code, 400)

    def test_the_preview_counts_what_is_carried(self):
        preview = self.client_for(self.carriere).get(
            f"{API}unites/{self.drh.pk}/suite/", {"date_effet": "2020-01-01"}
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json(), {
            "total": 2,
            "par_genre": [{"libelle": "départements", "nombre": 1},
                          {"libelle": "services", "nombre": 1}],
            "bloquants": [],
        })  # fmt: skip
        documents = (
            self.client_for(self.carriere)
            .get(f"{API}types-document/{self.dec.pk}/suite/", {"date_effet": "2020-01-01"})
            .json()
        )
        self.assertEqual(
            {g["libelle"]: g["nombre"] for g in documents["par_genre"]},
            {"pièces exigées": 1, "motifs de sortie": 1, "types de suspension": 1},
        )
        leaf = (
            self.client_for(self.carriere)
            .get(f"{API}echelons/{self.e1.pk}/suite/", {"date_effet": "2020-01-01"})
            .json()
        )
        self.assertEqual(leaf["total"], 0)

    def test_the_preview_needs_the_right_to_replace(self):
        url = f"{API}unites/{self.drh.pk}/suite/"
        self.assertEqual(self.client_for(self.auditeur).get(url, {"date_effet": "2020-01-01"})
                         .status_code, 403)  # fmt: skip
        self.assertEqual(self.client_for(self.carriere).get(url).status_code, 400)
        self.assertEqual(self.client_for(self.carriere).get(f"{API}sites/{self.kin.pk}/suite/",
                         {"date_effet": "2020-01-01"}).status_code, 405)  # fmt: skip
