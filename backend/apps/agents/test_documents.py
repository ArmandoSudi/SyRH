"""Scanned documents: the model and the upload checks.
See specs/2026-11-22-document-storage."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.audit.models import EntreeAudit
from apps.referentiels.models import Cle, Parametre, TypeDocument

from .documents import (
    FICHIER_VIDE,
    FORMAT_REFUSE,
    LIMITE_ABSENTE,
    TYPE_ILLISIBLE,
    clean_original_name,
    create_document,
    detect_mime,
)
from .models import (
    DEJA_RETIRE,
    DOCUMENT_DOUBLON,
    DOCUMENT_FIXE,
    MOTIF_COURT,
    Document,
)
from .test_affectations import D2015, agent, errors_of

PDF = b"%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
EXE = b"MZ\x90\x00" + b"\x00" * 32
HTML = b"<!doctype html><script>alert(1)</script>"
MO = 1024 * 1024


def upload(content=PDF, name="contrat.pdf", content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def user(username, *groups):
    account = get_user_model().objects.create_user(username, password="x")
    account.groups.set(Group.objects.filter(name__in=groups))
    return account


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.agent = agent()
        cls.other = agent("ARPTC/0002/2020", "Nsimba")
        cls.ctr = TypeDocument.objects.create(code="CTR", nom="Contrat signé", date_ouverture=D2015)
        cls.dip = TypeDocument.objects.create(code="DIP", nom="Diplôme", date_ouverture=D2015)
        cls.cmd = TypeDocument.objects.create(
            code="CMD", nom="Certificat médical", date_ouverture=D2015, confidentiel=True
        )
        cls.cmd.groupes_autorises.set([Group.objects.get(name="Social")])
        Parametre.objects.create(cle=Cle.TAILLE_MAX_PIECE, valeur=1, date_ouverture=D2015)
        cls.carriere = user("carriere", "Gestion de carrière")

    def document(self, content=PDF, name="contrat.pdf", type_document=None, agent=None, **kw):
        return create_document(
            agent or self.agent, type_document or self.ctr, upload(content, name), **kw
        )


class DetectionTests(TestCase):
    def test_accepted_formats(self):
        self.assertEqual(detect_mime(PDF), "application/pdf")
        self.assertEqual(detect_mime(JPEG), "image/jpeg")
        self.assertEqual(detect_mime(PNG), "image/png")

    def test_refused_formats(self):
        for content in (EXE, HTML, b"", b"GIF89a", b"PK\x03\x04"):
            self.assertIsNone(detect_mime(content))

    def test_clean_original_name(self):
        self.assertEqual(clean_original_name("../../etc/passwd.pdf"), "passwd.pdf")
        self.assertEqual(clean_original_name("C:\\Scans\\acte.pdf"), "acte.pdf")
        self.assertEqual(clean_original_name("ac\x00te\x1f\n.pdf"), "acte.pdf")
        self.assertEqual(clean_original_name("Décision n°12.pdf"), "Décision n°12.pdf")
        self.assertEqual(clean_original_name("", "image/png"), "piece.png")
        self.assertEqual(clean_original_name("..", "application/pdf"), "piece.pdf")
        long = clean_original_name("a" * 300 + ".pdf")
        self.assertEqual(len(long), 150)
        self.assertTrue(long.endswith(".pdf"))


class UploadTests(Base):
    def test_pdf_jpeg_png_accepted_from_their_content(self):
        pdf = self.document(PDF, "scan.png")  # wrong extension: the content decides
        jpeg = self.document(JPEG, "photo.jpg")
        png = self.document(PNG, "scan.pdf", type_document=self.dip)
        self.assertEqual(
            [pdf.type_mime, jpeg.type_mime, png.type_mime],
            ["application/pdf", "image/jpeg", "image/png"],
        )
        self.assertEqual(pdf.taille, len(PDF))
        self.assertRegex(pdf.empreinte, r"^[0-9a-f]{64}$")

    def test_file_round_trips_and_is_encrypted_on_disk(self):
        document = self.document()
        with document.fichier.open() as opened:
            self.assertEqual(opened.read(), PDF)
        with open(document.fichier.path, "rb") as raw:
            self.assertFalse(raw.read().startswith(b"%PDF"))

    def test_stored_name_is_a_uuid_whatever_the_original_name(self):
        document = self.document(name="../../etc/passwd.pdf")
        now = timezone.now()
        self.assertRegex(document.fichier.name, rf"^documents/{now:%Y}/{now:%m}/[0-9a-f]{{32}}$")
        self.assertEqual(document.nom_original, "passwd.pdf")

    def test_spoofed_and_empty_files_refused(self):
        for content in (EXE, HTML):
            errors = errors_of(lambda c=content: self.document(c, "facture.pdf"))
            self.assertEqual(errors, {"fichier": [FORMAT_REFUSE]})
        self.assertEqual(errors_of(lambda: self.document(b"")), {"fichier": [FICHIER_VIDE]})
        self.assertEqual(Document.objects.count(), 0)

    def test_size_limit_from_the_parameter(self):
        exact = PDF + b"0" * (MO - len(PDF))
        self.document(exact)
        errors = errors_of(lambda: self.document(exact + b"0", type_document=self.dip))
        self.assertEqual(errors, {"fichier": ["Le fichier dépasse la taille maximale de 1 Mo."]})
        row = Parametre.objects.get(cle=Cle.TAILLE_MAX_PIECE)
        row.valeur = 2
        row.save()
        self.document(exact + b"0", type_document=self.dip)

    def test_no_size_parameter(self):
        Parametre.objects.get(cle=Cle.TAILLE_MAX_PIECE).delete()
        self.assertEqual(errors_of(self.document), {"fichier": [LIMITE_ABSENTE]})

    def test_duplicate_refused_for_same_agent_and_type_only(self):
        self.document()
        self.assertEqual(errors_of(self.document), {"fichier": [DOCUMENT_DOUBLON]})
        self.document(type_document=self.dip)
        self.document(agent=self.other)

    def test_duplicate_accepted_after_retirement(self):
        first = self.document()
        first.retirer("Mauvais agent sélectionné")
        self.document()

    def test_duplicate_refused_by_the_database(self):
        first = self.document()
        copy = Document.objects.get(pk=first.pk)
        copy.pk = None
        with self.assertRaises(IntegrityError), transaction.atomic():
            Document._base_manager.bulk_create([copy])

    def test_closed_type_refused(self):
        self.ctr.date_fermeture = date(2020, 1, 1)
        self.ctr.save()
        errors = errors_of(self.document)
        self.assertIn("n'est pas ouvert", errors["type_document"][0])

    def test_confidential_type_needs_one_of_its_groups(self):
        errors = errors_of(lambda: self.document(type_document=self.cmd, auteur=self.carriere))
        self.assertEqual(errors, {"type_document": [TYPE_ILLISIBLE]})
        social = user("social", "Social")
        self.document(type_document=self.cmd, auteur=social)

    def test_refused_upload_leaves_no_file(self):
        self.document()
        before = set(self.list_files())
        errors_of(self.document)
        self.assertEqual(set(self.list_files()), before)

    def list_files(self):
        from django.conf import settings

        return [p for p in settings.SYRH_DOCUMENT_ROOT.rglob("*") if p.is_file()]


class ModelRulesTests(Base):
    def test_label(self):
        document = self.document(name="Contrat Mukendi.pdf")
        self.assertEqual(str(document), "CTR — Contrat Mukendi.pdf — ARPTC/0001/2020")

    def test_metadata_fixed(self):
        document = self.document()
        for name, value in (
            ("agent", self.other),
            ("type_document", self.dip),
            ("nom_original", "autre.pdf"),
            ("date_document", date(2020, 1, 1)),
        ):
            row = Document.objects.get(pk=document.pk)
            setattr(row, name, value)
            self.assertEqual(errors_of(row.save), {name: [DOCUMENT_FIXE]})

    def test_retire_once_with_a_reason(self):
        document = self.document()
        self.assertEqual(errors_of(lambda: document.retirer("court")), {"motif": [MOTIF_COURT]})
        document.retirer("  Mauvais agent sélectionné  ", auteur=self.carriere)
        document.refresh_from_db()
        self.assertTrue(document.retire)
        self.assertEqual(document.motif_retrait, "Mauvais agent sélectionné")
        self.assertEqual(document.retire_par, self.carriere)
        self.assertIsNotNone(document.date_retrait)
        errors = errors_of(lambda: document.retirer("Une seconde fois"))
        self.assertEqual(errors, {"motif": [DEJA_RETIRE]})

    def test_database_refuses_an_incoherent_retirement(self):
        document = self.document()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Document._base_manager.filter(pk=document.pk).update(retire=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Document._base_manager.filter(pk=document.pk).update(motif_retrait="Motif sans retrait")

    def test_database_refuses_bad_format_and_empty(self):
        document = self.document()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Document._base_manager.filter(pk=document.pk).update(type_mime="text/html")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Document._base_manager.filter(pk=document.pk).update(taille=0)

    def test_never_deleted(self):
        document = self.document()
        with self.assertRaises(PermissionError):
            document.delete()
        self.assertFalse(
            [p for p in Document._meta.default_permissions if p == "delete"],
        )


class LisiblesParTests(Base):
    def test_confidential_rows_by_group(self):
        social = user("social2", "Social")
        root = user("root")
        root.is_superuser = True
        root.save()
        self.document()
        self.document(type_document=self.cmd, name="certificat.pdf")
        self.assertEqual(Document.objects.lisibles_par(self.carriere).count(), 1)
        self.assertEqual(Document.objects.lisibles_par(social).count(), 2)
        self.assertEqual(Document.objects.lisibles_par(root).count(), 2)

    def test_no_duplicate_rows_for_a_user_in_several_groups(self):
        both = user("both", "Social", "Direction RH")
        self.cmd.groupes_autorises.add(Group.objects.get(name="Direction RH"))
        self.document(type_document=self.cmd)
        self.assertEqual(Document.objects.lisibles_par(both).count(), 1)


class AuditTests(Base):
    def test_upload_and_retirement_audited_without_content(self):
        document = self.document(name="contrat.pdf", auteur=self.carriere)
        document.retirer("Mauvais agent sélectionné", auteur=self.carriere)
        entries = EntreeAudit.objects.filter(
            objet_id=document.pk, module="agents", table__model="document"
        ).order_by("id")
        self.assertEqual([e.action for e in entries], ["creation", "modification"])
        for entry in entries:
            self.assertEqual(entry.auteur, self.carriere)
            self.assertEqual(entry.objet_libelle, "CTR — contrat.pdf — ARPTC/0001/2020")
            self.assertNotIn("endobj", str(entry.changements))
        champs = {c["champ"] for c in entries[1].changements}
        self.assertTrue({"retire", "motif_retrait"} <= champs)


class ReadBackTests(Base):
    def test_open_returns_the_clear_bytes(self):
        document = self.document(PNG, "scan.png")
        self.assertEqual(document.fichier.read(), PNG)
