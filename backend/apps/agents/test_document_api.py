"""The documents API. See specs/2026-11-22-document-storage (D14, D15, D18 to D20)."""

from cryptography.fernet import Fernet
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.core.storage import UNREADABLE
from apps.referentiels.models import Cle, Parametre, TypeDocument

from .documents import FORMAT_REFUSE, create_document
from .models import DOCUMENT_DOUBLON, MOTIF_COURT
from .test_access import member
from .test_affectations import D2015, agent
from .test_documents import EXE, HTML, JPEG, PDF, PNG

FIELDS = {
    "id", "type_document", "type_document_code", "type_document_nom", "confidentiel",
    "nom_original", "type_mime", "taille", "date_document", "retire", "motif_retrait",
    "date_retrait", "retire_par", "retire_par_nom", "cree_par_nom", "date_creation",
    "date_modification", "cree_par", "modifie_par",
}  # fmt: skip


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        Parametre.objects.create(cle=Cle.TAILLE_MAX_PIECE, valeur=1, date_ouverture=D2015)
        cls.agent = agent()
        cls.ctr = TypeDocument.objects.create(code="CTR", nom="Contrat signé", date_ouverture=D2015)
        cls.dip = TypeDocument.objects.create(code="DIP", nom="Diplôme", date_ouverture=D2015)
        cls.cmd = TypeDocument.objects.create(
            code="CMD", nom="Certificat médical", date_ouverture=D2015, confidentiel=True
        )
        cls.cmd.groupes_autorises.set(Group.objects.filter(name__in=["Social", "Direction RH"]))
        cls.carriere = member("carriere", "Gestion de carrière", first_name="Aline",
                              last_name="Mbuyi")  # fmt: skip
        cls.personnel = member("personnel", "Administration du personnel")
        cls.formation = member("formation", "Formation")
        cls.social = member("social", "Social")
        cls.direction = member("direction", "Direction RH")
        cls.auditeur = member("auditeur", "Auditeur")
        cls.admin = member("admin", "Administrateur système")
        cls.nobody = member("personne")

    def api(self, user):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client

    def url(self, suffix="", agent=None):
        return f"/api/agents/{(agent or self.agent).pk}/documents/{suffix}"

    def upload(self, user=None, content=PDF, name="Contrat Mukendi.pdf", type_document=None,
               **extra):  # fmt: skip
        data = {
            "type_document": (type_document or self.ctr).pk,
            "fichier": SimpleUploadedFile(name, content, content_type="application/pdf"),
            **extra,
        }
        return self.api(user or self.carriere).post(self.url(), data, format="multipart")

    def stored(self, content=PDF, name="contrat.pdf", type_document=None):
        return create_document(
            self.agent, type_document or self.ctr, SimpleUploadedFile(name, content)
        )


class ListTests(Base):
    def test_fields_and_order_newest_first(self):
        first = self.stored(PDF, "a.pdf")
        second = self.stored(PNG, "b.png", type_document=self.dip)
        rows = self.api(self.formation).get(self.url()).json()
        self.assertEqual([row["id"] for row in rows], [second.pk, first.pk])
        self.assertEqual(set(rows[0]), FIELDS)
        self.assertEqual(rows[0]["type_document_code"], "DIP")
        self.assertEqual(rows[0]["type_mime"], "image/png")
        self.assertNotIn("fichier", rows[0])
        self.assertNotIn("empreinte", rows[0])

    def test_retired_only_on_request(self):
        kept = self.stored(PDF, "a.pdf")
        retired = self.stored(PNG, "b.png")
        retired.retirer("Mauvais agent sélectionné", auteur=self.carriere)
        default = self.api(self.carriere).get(self.url()).json()
        self.assertEqual([row["id"] for row in default], [kept.pk])
        everything = self.api(self.carriere).get(self.url("?retires=1")).json()
        self.assertEqual({row["id"] for row in everything}, {kept.pk, retired.pk})
        row = next(row for row in everything if row["id"] == retired.pk)
        self.assertEqual(row["retire_par_nom"], "Aline Mbuyi")

    def test_confidential_absent_for_non_members(self):
        certificat = self.stored(PDF, "certificat.pdf", type_document=self.cmd)
        for user in (self.carriere, self.formation, self.auditeur):
            with self.subTest(user.username):
                self.assertEqual(self.api(user).get(self.url()).json(), [])
                fichier = self.api(user).get(self.url(f"{certificat.pk}/fichier/"))
                self.assertEqual(fichier.status_code, 404)
        for user in (self.social, self.direction):
            with self.subTest(user.username):
                rows = self.api(user).get(self.url()).json()
                self.assertEqual([row["id"] for row in rows], [certificat.pk])
                self.assertTrue(rows[0]["confidentiel"])

    def test_fixed_number_of_queries(self):
        self.stored(PDF, "a.pdf")
        client = self.api(self.carriere)
        client.get(self.url())  # the user's permissions are cached from here on
        with CaptureQueriesContext(connection) as one:
            client.get(self.url())
        self.stored(PNG, "b.png")
        retired = self.stored(JPEG, "c.jpg")
        retired.retirer("Mauvais agent sélectionné", auteur=self.carriere)
        with CaptureQueriesContext(connection) as three:
            client.get(self.url("?retires=1"))
        self.assertEqual(len(one), len(three))


class UploadTests(Base):
    def test_upload_returns_the_row(self):
        response = self.upload(date_document="2021-03-01")
        self.assertEqual(response.status_code, 201, response.json())
        row = response.json()
        self.assertEqual(row["nom_original"], "Contrat Mukendi.pdf")
        self.assertEqual(row["type_mime"], "application/pdf")
        self.assertEqual(row["date_document"], "2021-03-01")
        self.assertEqual(row["cree_par"], self.carriere.pk)
        self.assertEqual(row["cree_par_nom"], "Aline Mbuyi")

    def test_administration_du_personnel_uploads_too(self):
        self.assertEqual(self.upload(self.personnel).status_code, 201)

    def test_refusals_on_their_field(self):
        cases = [
            ({"content": EXE, "name": "facture.pdf"}, "fichier", FORMAT_REFUSE),
            ({"content": HTML, "name": "page.pdf"}, "fichier", FORMAT_REFUSE),
            ({"content": PDF + b"0" * (1024 * 1024)}, "fichier",
             "Le fichier dépasse la taille maximale de 1 Mo."),
            ({"content": b""}, "fichier", "Le fichier est vide."),
        ]  # fmt: skip
        for kwargs, field, message in cases:
            with self.subTest(message):
                response = self.upload(**kwargs)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()[field], [message])

    def test_duplicate_refused(self):
        self.upload()
        response = self.upload()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["fichier"], [DOCUMENT_DOUBLON])

    def test_missing_fields(self):
        response = self.api(self.carriere).post(self.url(), {}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"type_document", "fichier"})

    def test_confidential_type_refused_without_its_group(self):
        response = self.upload(type_document=self.cmd)
        self.assertEqual(response.status_code, 400)
        self.assertIn("type_document", response.json())

    def test_path_traversal_name_cleaned(self):
        response = self.upload(name="../../etc/passwd.pdf")
        self.assertEqual(response.json()["nom_original"], "passwd.pdf")


class DownloadTests(Base):
    def test_inline_and_attachment(self):
        document = self.stored(PDF, "Décision n°12.pdf")
        inline = self.api(self.formation).get(self.url(f"{document.pk}/fichier/"))
        self.assertEqual(inline.status_code, 200)
        self.assertEqual(inline.content, PDF)
        self.assertEqual(inline["Content-Type"], "application/pdf")
        self.assertTrue(inline["Content-Disposition"].startswith("inline"))
        self.assertIn(
            "filename*=utf-8''D%C3%A9cision%20n%C2%B012.pdf", inline["Content-Disposition"]
        )
        self.assertEqual(inline["X-Content-Type-Options"], "nosniff")
        self.assertEqual(inline["Cache-Control"], "private, no-store")
        attached = self.api(self.formation).get(
            self.url(f"{document.pk}/fichier/?telechargement=1")
        )
        self.assertTrue(attached["Content-Disposition"].startswith("attachment"))

    def test_stored_type_whatever_the_name(self):
        document = self.stored(PNG, "scan.pdf")
        response = self.api(self.carriere).get(self.url(f"{document.pk}/fichier/"))
        self.assertEqual(response["Content-Type"], "image/png")

    def test_retired_still_downloads(self):
        document = self.stored()
        document.retirer("Mauvais agent sélectionné")
        response = self.api(self.carriere).get(self.url(f"{document.pk}/fichier/"))
        self.assertEqual(response.content, PDF)

    def test_document_of_another_agent_is_404(self):
        document = self.stored()
        other = agent("ARPTC/0002/2020", "Nsimba")
        response = self.api(self.carriere).get(self.url(f"{document.pk}/fichier/", agent=other))
        self.assertEqual(response.status_code, 404)

    def test_undecryptable_file_is_500_without_its_bytes(self):
        document = self.stored()
        with open(document.fichier.path, "wb") as raw:
            raw.write(Fernet(Fernet.generate_key()).encrypt(PDF))
        with self.assertLogs("apps.agents.document_views", "ERROR"):
            response = self.api(self.carriere).get(self.url(f"{document.pk}/fichier/"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": UNREADABLE})
        self.assertNotIn(b"%PDF", response.content)


class RetraitTests(Base):
    def test_retire_then_refuse_a_second_time(self):
        document = self.stored()
        url = self.url(f"{document.pk}/retrait/")
        short = self.api(self.carriere).post(url, {"motif": "court"}, format="json")
        self.assertEqual(short.status_code, 400)
        self.assertEqual(short.json()["motif"], [MOTIF_COURT])
        done = self.api(self.carriere).post(
            url, {"motif": "Mauvais agent sélectionné"}, format="json"
        )
        self.assertEqual(done.status_code, 200)
        self.assertTrue(done.json()["retire"])
        self.assertEqual(done.json()["retire_par"], self.carriere.pk)
        again = self.api(self.carriere).post(url, {"motif": "Une autre raison"}, format="json")
        self.assertEqual(again.status_code, 400)


class AccessTests(Base):
    def test_anonymous_401(self):
        self.assertEqual(self.api(None).get(self.url()).status_code, 401)
        self.assertEqual(self.api(None).post(self.url(), {}).status_code, 401)

    def test_without_agents_403_even_for_an_unknown_agent(self):
        for user in (self.admin, self.nobody):
            with self.subTest(user.username):
                self.assertEqual(self.api(user).get(self.url()).status_code, 403)
                self.assertEqual(
                    self.api(user).get("/api/agents/999999/documents/").status_code, 403
                )

    def test_unknown_agent_404_for_a_reader(self):
        self.assertEqual(
            self.api(self.formation).get("/api/agents/999999/documents/").status_code, 404
        )

    def test_readers_without_rights_cannot_upload_or_retire(self):
        document = self.stored()
        for user in (self.formation, self.auditeur, self.social, self.direction):
            with self.subTest(user.username):
                self.assertEqual(self.upload(user).status_code, 403)
                response = self.api(user).post(
                    self.url(f"{document.pk}/retrait/"),
                    {"motif": "Mauvais agent sélectionné"},
                    format="json",
                )
                self.assertEqual(response.status_code, 403)

    def test_other_methods_405(self):
        document = self.stored()
        client = self.api(self.carriere)
        for method in ("put", "patch", "delete"):
            with self.subTest(method):
                self.assertEqual(getattr(client, method)(self.url()).status_code, 405)
                self.assertEqual(
                    getattr(client, method)(self.url(f"{document.pk}/fichier/")).status_code, 405
                )

    def test_agent_endpoints_unchanged(self):
        self.stored()
        detail = self.api(self.carriere).get(f"/api/agents/{self.agent.pk}/").json()
        self.assertNotIn("documents", detail)
