"""The agent record (roadmap milestone 2).

Agent identity: specs/2026-11-21-agent-identity.

Rules that only read the row itself are database constraints; rules that read
other rows or today's date live in check_rules(), called by clean() and save().
The matricule is fixed and an agent is never deleted: two PostgreSQL triggers
(migration 0002) refuse it even outside Django.
"""

import re
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Upper
from django.utils import timezone

from apps.core.models import NO_DELETE, BaseModel

MATRICULE_PATTERN = r"^[A-Z0-9/.-]{1,20}$"
MATRICULE_HELP = "Lettres, chiffres, « / », « - » et « . », 20 caractères au plus."
MATRICULE_TAKEN = "Ce matricule est déjà attribué à un autre agent."
MATRICULE_FIXED = "Le matricule ne peut pas être modifié."
NEVER_DELETED = "Un agent n'est jamais supprimé : son matricule ne doit pas être réutilisé."
BIRTH_FUTURE = "La date de naissance ne peut pas être dans le futur."
EARLIEST_BIRTH = date(1900, 1, 1)


class Agent(BaseModel):
    """One ARPTC agent, identified by a matricule unique and never reused
    (agent identity D2, D7 to D10, SOC-01).

    The matricule is typed by HR, stored trimmed and in capitals, and cannot
    change; an agent is never deleted, so a matricule is never freed.
    """

    module = "agents"

    class Sexe(models.TextChoices):
        MASCULIN = "M", "Masculin"
        FEMININ = "F", "Féminin"

    matricule = models.CharField("matricule", max_length=20, help_text=MATRICULE_HELP)
    nom = models.CharField("nom", max_length=100)
    postnom = models.CharField("postnom", max_length=100, blank=True)
    prenom = models.CharField("prénom", max_length=100, blank=True)
    sexe = models.CharField("sexe", max_length=1, choices=Sexe.choices)
    date_naissance = models.DateField("date de naissance")
    lieu_naissance = models.CharField("lieu de naissance", max_length=150)
    nationalite = models.CharField("nationalité", max_length=100, default="Congolaise")

    class Meta:
        verbose_name = "agent"
        verbose_name_plural = "agents"
        ordering = ["nom", "postnom", "prenom", "matricule"]  # D6
        default_permissions = NO_DELETE
        constraints = [
            models.UniqueConstraint(
                Upper("matricule"),
                name="agent_matricule_unique",
                violation_error_message=MATRICULE_TAKEN,
            ),
            models.CheckConstraint(
                condition=Q(matricule__regex=MATRICULE_PATTERN),
                name="agent_matricule_valide",
                violation_error_message=MATRICULE_HELP,
            ),
            models.CheckConstraint(
                condition=Q(nom__regex=r"\S"),
                name="agent_nom_renseigne",
                violation_error_message="Le nom est obligatoire.",
            ),
            models.CheckConstraint(
                condition=Q(sexe__in=["M", "F"]),
                name="agent_sexe_valide",
                violation_error_message="Sexe inconnu.",
            ),
            models.CheckConstraint(
                condition=Q(date_naissance__gte=EARLIEST_BIRTH),
                name="agent_naissance_apres_1900",
                violation_error_message="La date de naissance doit être après 1900.",
            ),
        ]

    def __str__(self):
        noms = " ".join(part for part in (self.nom, self.postnom, self.prenom) if part)
        return f"{self.matricule} — {noms}"

    def normalise(self) -> None:
        if self.matricule:
            self.matricule = self.matricule.strip().upper()
        for name in ("nom", "postnom", "prenom", "lieu_naissance", "nationalite"):
            value = getattr(self, name)
            if value:
                setattr(self, name, value.strip())

    def check_rules(self) -> None:
        errors: dict[str, list[str]] = {}
        if self.matricule:
            if not re.fullmatch(MATRICULE_PATTERN, self.matricule):
                errors["matricule"] = [MATRICULE_HELP]
            else:
                others = type(self)._base_manager.filter(matricule__iexact=self.matricule)
                if self.pk is not None:
                    others = others.exclude(pk=self.pk)
                if others.exists():
                    errors["matricule"] = [MATRICULE_TAKEN]
        if self.pk is not None:
            old = (
                type(self)
                ._base_manager.filter(pk=self.pk)
                .values_list("matricule", flat=True)
                .first()
            )
            if old is not None and old != self.matricule:
                errors["matricule"] = [MATRICULE_FIXED]
        if isinstance(self.date_naissance, date) and self.date_naissance > timezone.localdate():
            errors["date_naissance"] = [BIRTH_FUTURE]
        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        self.normalise()
        self.check_rules()

    def save(self, **kwargs):
        self.normalise()
        self.check_rules()
        super().save(**kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(NEVER_DELETED)
