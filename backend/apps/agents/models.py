"""The agent record (roadmap milestone 2).

Agent identity: specs/2026-11-21-agent-identity.
Contact details: specs/2026-11-21-contact-details.

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


# An optional leading +, then digits and single spaces, 8 to 20 characters
# (contact details D7). Python and PostgreSQL both read the lookahead.
PHONE_PATTERN = r"^(?=.{8,20}$)\+?[0-9]+( [0-9]+)*$"
PHONE_HELP = "Chiffres et espaces, avec un « + » au début si besoin, de 8 à 20 caractères."
URGENCE_PAIR = "Le nom et le téléphone de la personne à contacter vont ensemble."
AGENT_FIXED = "Les coordonnées ne peuvent pas passer à un autre agent."
COORDONNEES_NEVER_DELETED = "Les coordonnées d'un agent ne sont jamais supprimées : corrigez-les."
PHONES = ("telephone", "telephone_secondaire", "urgence_telephone")


def phone_ok(field: str) -> Q:
    return Q(**{f"{field}__regex": PHONE_PATTERN})


class Coordonnees(BaseModel):
    """An agent's address, phones, email and emergency contact (contact details D1 to D10).

    At most one row per agent; current values, corrected in place (D3). The
    audit log keeps the old ones. Never deleted (D13).
    """

    module = "agents"

    agent = models.OneToOneField(
        Agent, verbose_name="agent", on_delete=models.PROTECT, related_name="coordonnees"
    )
    adresse = models.CharField("adresse", max_length=200, help_text="Avenue et numéro.")
    commune = models.CharField("commune", max_length=100, blank=True)
    ville = models.CharField("ville", max_length=100)
    telephone = models.CharField("téléphone", max_length=20, help_text=PHONE_HELP)
    telephone_secondaire = models.CharField(
        "second téléphone", max_length=20, blank=True, help_text=PHONE_HELP
    )
    courriel = models.EmailField("courriel", blank=True)
    urgence_nom = models.CharField(
        "personne à contacter en cas d'urgence", max_length=150, blank=True
    )
    urgence_lien = models.CharField(
        "lien avec l'agent", max_length=50, blank=True, help_text="Par exemple : Épouse, Frère."
    )
    urgence_telephone = models.CharField(
        "téléphone de la personne à contacter", max_length=20, blank=True, help_text=PHONE_HELP
    )

    class Meta:
        verbose_name = "coordonnées"
        verbose_name_plural = "coordonnées"
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(adresse__regex=r"\S") & Q(ville__regex=r"\S"),
                name="coordonnees_adresse_renseignee",
                violation_error_message="L'adresse et la ville sont obligatoires.",
            ),
            models.CheckConstraint(
                condition=phone_ok("telephone"),
                name="coordonnees_telephone_valide",
                violation_error_message=PHONE_HELP,
            ),
            models.CheckConstraint(
                condition=Q(telephone_secondaire="") | phone_ok("telephone_secondaire"),
                name="coordonnees_telephone_secondaire_valide",
                violation_error_message=PHONE_HELP,
            ),
            models.CheckConstraint(
                condition=Q(urgence_nom="", urgence_telephone="")
                | (Q(urgence_nom__regex=r"\S") & phone_ok("urgence_telephone")),
                name="coordonnees_urgence_complete",
                violation_error_message=URGENCE_PAIR,
            ),
        ]

    def __str__(self):
        agent = self.agent if self.agent_id else "?"
        return f"Coordonnées de {agent}"

    def normalise(self) -> None:
        for name in ("adresse", "commune", "ville", "urgence_nom", "urgence_lien"):
            setattr(self, name, (getattr(self, name) or "").strip())
        for name in PHONES:
            setattr(self, name, " ".join((getattr(self, name) or "").split()))
        self.courriel = (self.courriel or "").strip().lower()

    def check_rules(self) -> None:
        errors: dict[str, list[str]] = {}
        for name in PHONES:
            value = getattr(self, name)
            if value and not re.fullmatch(PHONE_PATTERN, value):
                errors[name] = [PHONE_HELP]
        if self.urgence_nom and not self.urgence_telephone:
            errors["urgence_telephone"] = [URGENCE_PAIR]
        elif self.urgence_telephone and not self.urgence_nom:
            errors["urgence_nom"] = [URGENCE_PAIR]
        if self.pk is not None:
            old = (
                type(self)
                ._base_manager.filter(pk=self.pk)
                .values_list("agent_id", flat=True)
                .first()
            )
            if old is not None and old != self.agent_id:
                errors["agent"] = [AGENT_FIXED]
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
        raise PermissionError(COORDONNEES_NEVER_DELETED)
