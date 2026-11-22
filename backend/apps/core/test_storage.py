"""Encrypted document storage. See specs/2026-11-22-document-storage (D7 to D10)."""

import tempfile

from cryptography.fernet import Fernet
from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from .checks import document_key_errors
from .storage import DocumentIndechiffrable, EncryptedFileSystemStorage

PDF = b"%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"


class StorageTests(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="syrh-storage-test-")
        self.key = Fernet.generate_key().decode()
        self.storage = EncryptedFileSystemStorage(location=self.root, keys=[self.key])

    def raw(self, name: str) -> bytes:
        with open(self.storage.path(name), "rb") as stored:
            return stored.read()

    def test_round_trip(self):
        name = self.storage.save("documents/test", ContentFile(PDF))
        with self.storage.open(name) as opened:
            self.assertEqual(opened.read(), PDF)
        self.assertEqual(self.storage.size(name), len(PDF))

    def test_bytes_on_disk_are_not_the_document(self):
        name = self.storage.save("documents/test", ContentFile(PDF))
        raw = self.raw(name)
        self.assertNotEqual(raw, PDF)
        self.assertFalse(raw.startswith(b"%PDF-"))
        self.assertNotIn(b"endobj", raw)

    def test_rotation_keeps_old_files_and_uses_the_new_key(self):
        old_name = self.storage.save("documents/old", ContentFile(PDF))
        new_key = Fernet.generate_key().decode()
        rotated = EncryptedFileSystemStorage(location=self.root, keys=[new_key, self.key])
        with rotated.open(old_name) as opened:
            self.assertEqual(opened.read(), PDF)
        new_name = rotated.save("documents/new", ContentFile(PDF))
        new_only = EncryptedFileSystemStorage(location=self.root, keys=[new_key])
        with new_only.open(new_name) as opened:
            self.assertEqual(opened.read(), PDF)

    def test_unknown_key_raises(self):
        name = self.storage.save("documents/test", ContentFile(PDF))
        other = EncryptedFileSystemStorage(
            location=self.root, keys=[Fernet.generate_key().decode()]
        )
        with self.assertRaises(DocumentIndechiffrable):
            other.open(name)

    def test_no_public_url(self):
        name = self.storage.save("documents/test", ContentFile(PDF))
        with self.assertRaises(NotImplementedError):
            self.storage.url(name)

    def test_read_only(self):
        name = self.storage.save("documents/test", ContentFile(PDF))
        with self.assertRaises(ValueError):
            self.storage.open(name, "wb")


class KeyCheckTests(SimpleTestCase):
    def test_missing_key(self):
        errors = document_key_errors([])
        self.assertEqual([error.id for error in errors], ["core.E002"])

    def test_malformed_key(self):
        errors = document_key_errors([Fernet.generate_key().decode(), "pas-une-cle"])
        self.assertEqual([error.id for error in errors], ["core.E002"])
        self.assertIn("number 2", errors[0].msg)

    def test_valid_keys(self):
        self.assertEqual(document_key_errors([Fernet.generate_key().decode()]), [])
