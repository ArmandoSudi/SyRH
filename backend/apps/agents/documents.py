"""Uploading a scanned document: the checks of document storage D4, D6, D11, D12.

Every upload goes through create_document(), from the API and the demo data, so
the format is read from the content, the size checked against the general
parameter, and the original name cleaned, whatever the client claims.
"""

import hashlib
import re
import unicodedata
from datetime import date

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.referentiels.models import Cle, Parametre, ParametreManquant

from .models import DOCUMENT_DOUBLON, Agent, Document

# The first bytes of each accepted format (D11).
SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)
EXTENSIONS = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}
NOM_MAX = 150
FORMAT_REFUSE = "Format refusé : seuls les fichiers PDF, JPEG et PNG sont acceptés."
FICHIER_VIDE = "Le fichier est vide."
TROP_GROS = "Le fichier dépasse la taille maximale de {mo} Mo."
LIMITE_ABSENTE = (
    "La taille maximale des pièces n'est pas paramétrée : demandez-la à un gestionnaire des "
    "référentiels."
)
TYPE_ILLISIBLE = "Vous ne pouvez pas déposer de pièce de ce type."


def detect_mime(head: bytes) -> str | None:
    """The format of a file from its first bytes, or None when not accepted (D11)."""
    for signature, mime in SIGNATURES:
        if head.startswith(signature):
            return mime
    return None


def clean_original_name(name: str, mime: str | None = None) -> str:
    """The uploaded name without any path or control character, 150 characters at
    most, keeping its extension (D4). An empty result becomes "piece" plus the
    extension of the detected format."""
    name = unicodedata.normalize("NFC", name or "")
    name = re.split(r"[\\/]", name)[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = " ".join(name.split()).strip(" .")
    if not name:
        name = "piece" + EXTENSIONS.get(mime or "", "")
    if len(name) > NOM_MAX:
        stem, dot, ext = name.rpartition(".")
        if dot and 0 < len(ext) <= 10:
            name = stem[: NOM_MAX - len(ext) - 1] + "." + ext
        else:
            name = name[:NOM_MAX]
    return name


def taille_max(jour: date) -> int:
    """The size limit in bytes on a day, from the general parameter (D12)."""
    try:
        return Parametre.valeur_au(Cle.TAILLE_MAX_PIECE, jour) * 1024 * 1024
    except ParametreManquant as error:
        raise ValidationError({"fichier": [LIMITE_ABSENTE]}) from error


def create_document(
    agent: Agent,
    type_document,
    uploaded_file,
    date_document: date | None = None,
    auteur=None,
) -> Document:
    """Check an uploaded file and store it encrypted for an agent (D1 to D6, D11, D12).

    Every refusal is a ValidationError on its field, in French.
    """
    if auteur is not None and not type_document.lisible_par(auteur):
        raise ValidationError({"type_document": [TYPE_ILLISIBLE]})

    limit = taille_max(timezone.localdate())
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > limit:  # before reading a too-large file
        raise ValidationError({"fichier": [TROP_GROS.format(mo=limit // (1024 * 1024))]})
    uploaded_file.seek(0)
    content = uploaded_file.read()
    if not content:
        raise ValidationError({"fichier": [FICHIER_VIDE]})
    if len(content) > limit:
        raise ValidationError({"fichier": [TROP_GROS.format(mo=limit // (1024 * 1024))]})
    mime = detect_mime(content[:16])
    if mime is None:
        raise ValidationError({"fichier": [FORMAT_REFUSE]})

    empreinte = hashlib.sha256(content).hexdigest()
    document = Document(
        agent=agent,
        type_document=type_document,
        nom_original=clean_original_name(getattr(uploaded_file, "name", ""), mime),
        type_mime=mime,
        taille=len(content),
        empreinte=empreinte,
        date_document=date_document,
        cree_par=auteur,
        modifie_par=auteur,
    )
    duplicate = Document.objects.filter(
        agent=agent, type_document=type_document, empreinte=empreinte, retire=False
    )
    if duplicate.exists():
        raise ValidationError({"fichier": [DOCUMENT_DOUBLON]})
    document.full_clean(exclude=["fichier"], validate_constraints=False)

    try:
        with transaction.atomic():
            document.fichier.save("piece", ContentFile(content), save=False)
            document.save()
    except Exception as error:
        # No row, so no file: remove what was written before the refusal.
        if document.fichier.name:
            document.fichier.storage.delete(document.fichier.name)
        if isinstance(error, IntegrityError):  # a concurrent upload of the same file
            raise ValidationError({"fichier": [DOCUMENT_DOUBLON]}) from error
        raise
    return document
