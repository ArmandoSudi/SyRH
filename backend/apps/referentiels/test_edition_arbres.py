"""Editing the tree reference tables through the API.

See specs/2026-11-20-tree-reference-screens.
"""

from datetime import date

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
