"""The agent record (roadmap milestone 2).

Agent identity: specs/2026-11-21-agent-identity.
Contact details: specs/2026-11-21-contact-details.
Contracts: specs/2026-11-21-contract.

Rules that only read the row itself are database constraints; rules that read
other rows or today's date live in check_rules(), called by clean() and save().
The matricule is fixed and an agent is never deleted: two PostgreSQL triggers
(migration 0002) refuse it even outside Django.
"""

import re
from datetime import date

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Min, Q, Value
from django.db.models.functions import Upper
from django.utils import timezone

from apps.core.models import NO_DELETE, BaseModel
from apps.referentiels.models import DateRange, fr

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

    def _contrats(self):
        """The contracts prefetched with the agent, or None when not prefetched."""
        return getattr(self, "_prefetched_objects_cache", {}).get("contrats")

    @property
    def date_engagement(self) -> date | None:
        """The start of the agent's first contract, never stored (contract D10)."""
        if self.pk is None:
            return None
        prefetched = self._contrats()
        if prefetched is not None:
            return min((c.date_debut for c in prefetched), default=None)
        return self.contrats.aggregate(debut=Min("date_debut"))["debut"]

    def contrat_au(self, jour: date) -> "Contrat | None":
        """The contract in force on a day, or None (contract D11)."""
        if self.pk is None:
            return None
        prefetched = self._contrats()
        if prefetched is not None:
            return next((c for c in prefetched if c.en_vigueur(jour)), None)
        return (
            self.contrats.filter(date_debut__lte=jour)
            .filter(Q(date_fin__isnull=True) | Q(date_fin__gte=jour))
            .first()
        )

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


CONTRAT_OVERLAP = "Cet agent a déjà un contrat sur une partie de cette période."
FIN_AVANT_DEBUT = "La date de fin ne peut pas précéder la date de début."
ESSAI_HORS_CONTRAT = "La fin de la période d'essai doit tomber pendant le contrat."
FIN_OBLIGATOIRE = "Obligatoire : ce type de contrat est à durée déterminée."
FIN_INTERDITE = "Ce type de contrat est à durée indéterminée : pas de date de fin."
ESSAI_INTERDIT = "Ce type de contrat ne comporte pas de période d'essai."
CONTRAT_AGENT_FIXED = "Un contrat ne peut pas passer à un autre agent."
CONTRAT_NEVER_DELETED = "Un contrat n'est jamais supprimé : corrigez-le."


def type_ferme(type_contrat, jour: date) -> bool:
    return type_contrat.date_ouverture > jour or (
        type_contrat.date_fermeture is not None and type_contrat.date_fermeture <= jour
    )


class Contrat(BaseModel):
    """One of an agent's successive contracts (contract D1 to D9).

    date_fin and fin_periode_essai are last days, included, as printed on the
    signed contract (D3): unlike the reference tables, a successor starts the
    day after date_fin. One agent's contracts never overlap (D2).
    """

    module = "agents"

    agent = models.ForeignKey(
        Agent, verbose_name="agent", on_delete=models.PROTECT, related_name="contrats"
    )
    type_contrat = models.ForeignKey(
        "referentiels.TypeContrat",
        verbose_name="type de contrat",
        on_delete=models.PROTECT,
        related_name="+",
    )
    date_debut = models.DateField("date de début", help_text="Premier jour du contrat.")
    date_fin = models.DateField(
        "date de fin",
        null=True,
        blank=True,
        help_text="Dernier jour du contrat. Seulement pour un contrat à durée déterminée.",
    )
    fin_periode_essai = models.DateField(
        "fin de la période d'essai",
        null=True,
        blank=True,
        help_text="Dernier jour de la période d'essai, si le type en comporte une.",
    )

    class Meta:
        verbose_name = "contrat"
        verbose_name_plural = "contrats"
        ordering = ["agent", "date_debut"]  # D5
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(date_fin__isnull=True) | Q(date_fin__gte=F("date_debut")),
                name="contrat_fin_apres_debut",
                violation_error_message=FIN_AVANT_DEBUT,
            ),
            models.CheckConstraint(
                condition=Q(fin_periode_essai__isnull=True)
                | (
                    Q(fin_periode_essai__gte=F("date_debut"))
                    & (Q(date_fin__isnull=True) | Q(fin_periode_essai__lte=F("date_fin")))
                ),
                name="contrat_essai_pendant_le_contrat",
                violation_error_message=ESSAI_HORS_CONTRAT,
            ),
            ExclusionConstraint(
                name="contrat_sans_chevauchement",
                expressions=[
                    ("agent", RangeOperators.EQUAL),
                    (
                        DateRange("date_debut", "date_fin", Value("[]")),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                violation_error_message=CONTRAT_OVERLAP,
            ),
        ]

    def __str__(self):
        code = self.type_contrat.code if self.type_contrat_id else "?"
        matricule = self.agent.matricule if self.agent_id else "?"
        debut = fr(self.date_debut) if self.date_debut else "?"
        if self.date_fin:
            return f"{code} du {debut} au {fr(self.date_fin)} — {matricule}"
        return f"{code} depuis le {debut} — {matricule}"

    def en_vigueur(self, jour: date) -> bool:
        return self.date_debut <= jour and (self.date_fin is None or jour <= self.date_fin)

    def check_rules(self) -> None:
        """Rules on the dates and from the type (D3, D4, D6 to D8, D13).

        Reversed dates are reported on their field before the exclusion
        constraint runs: a daterange whose end precedes its start is a
        PostgreSQL error, not a message.
        """
        errors: dict[str, list[str]] = {}
        debut, fin, essai = self.date_debut, self.date_fin, self.fin_periode_essai
        if debut and fin and fin < debut:
            errors["date_fin"] = [FIN_AVANT_DEBUT]
        if essai and debut and (essai < debut or (fin and essai > fin)):
            errors["fin_periode_essai"] = [ESSAI_HORS_CONTRAT]

        if self.type_contrat_id:
            type_contrat = self.type_contrat
            if debut and type_ferme(type_contrat, debut):
                errors["type_contrat"] = [
                    f"Le type « {type_contrat.code} » n'est pas ouvert le {fr(debut)}."
                ]
            if type_contrat.duree_determinee and not fin:
                errors.setdefault("date_fin", []).append(FIN_OBLIGATOIRE)
            elif not type_contrat.duree_determinee and fin:
                errors.setdefault("date_fin", []).append(FIN_INTERDITE)
            if essai and not type_contrat.periode_essai:
                errors.setdefault("fin_periode_essai", []).append(ESSAI_INTERDIT)

        if self.pk is not None:
            old = (
                type(self)
                ._base_manager.filter(pk=self.pk)
                .values_list("agent_id", flat=True)
                .first()
            )
            if old is not None and old != self.agent_id:
                errors["agent"] = [CONTRAT_AGENT_FIXED]
        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        self.check_rules()

    def save(self, **kwargs):
        self.check_rules()
        super().save(**kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(CONTRAT_NEVER_DELETED)
