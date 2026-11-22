"""Encrypted storage of the scanned documents (document storage D7 to D10).

Files are encrypted with Fernet before they reach the disk and decrypted in
memory when read; the keys come from settings.SYRH_DOCUMENT_KEYS. The storage has
no public URL: only the authenticated documents endpoints serve its files.
"""

from functools import cached_property

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

UNREADABLE = (
    "Ce document ne peut pas être déchiffré : la clé de chiffrement a changé ou le fichier "
    "est abîmé. Prévenez l'administrateur."
)


class DocumentIndechiffrable(Exception):
    """A stored file that none of the keys decrypts (D10)."""


def fernet(keys: list[str] | None = None) -> MultiFernet:
    """The keys as one MultiFernet: the first encrypts, all decrypt (D8)."""
    keys = settings.SYRH_DOCUMENT_KEYS if keys is None else keys
    return MultiFernet([Fernet(key.strip().encode()) for key in keys])


@deconstructible
class EncryptedFileSystemStorage(FileSystemStorage):
    """FileSystemStorage that encrypts on save and decrypts on open (D7, D10).

    open() returns a ContentFile holding the clear bytes, read whole: documents
    are 50 Mo at most (D12). A file no key decrypts raises DocumentIndechiffrable,
    so ciphertext is never served as a document.
    """

    def __init__(self, location=None, keys: list[str] | None = None):
        self._keys = keys
        super().__init__(location=location, base_url=None)

    @cached_property
    def base_location(self):
        return self._value_or_setting(self._location, settings.SYRH_DOCUMENT_ROOT)

    @property
    def fernet(self) -> MultiFernet:
        return fernet(self._keys)

    def _save(self, name, content):
        content.seek(0)
        token = self.fernet.encrypt(content.read())
        return super()._save(name, ContentFile(token))

    def _open(self, name, mode="rb"):
        if "w" in mode or "a" in mode or "+" in mode:
            raise ValueError("Les documents chiffrés s'ouvrent en lecture seule.")
        with super()._open(name, "rb") as stored:
            token = stored.read()
        try:
            clear = self.fernet.decrypt(token)
        except InvalidToken as error:
            raise DocumentIndechiffrable(UNREADABLE) from error
        return ContentFile(clear, name=name)

    def size(self, name):
        """The size of the clear file, by decrypting it."""
        return self._open(name).size

    def url(self, name):
        raise NotImplementedError("Les documents n'ont pas d'adresse publique (D9).")


document_storage = EncryptedFileSystemStorage()


def get_document_storage() -> EncryptedFileSystemStorage:
    """The storage of Document.fichier, as a callable so migrations do not embed it."""
    return document_storage
