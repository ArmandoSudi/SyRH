"""The agent record (roadmap milestone 2).

Agent identity: specs/2026-11-21-agent-identity.
Contact details: specs/2026-11-21-contact-details.
Contracts: specs/2026-11-21-contract.
Assignments and classifications: specs/2026-11-21-position-history.
Bank accounts: specs/2026-11-21-bank-account.
Documents: specs/2026-11-22-document-storage.
Documents on events: specs/2026-11-22-documents-on-events.

Rules that only read the row itself are database constraints; rules that read
other rows or today's date live in check_rules(), called by clean() and save().
The matricule is fixed and an agent is never deleted: two PostgreSQL triggers
(migration 0002) refuse it even outside Django.
"""

import re
import uuid
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, Exists, F, Min, OuterRef, Q, Value, When
from django.db.models.functions import Upper
from django.utils import timezone

from apps.core.models import NO_DELETE, BaseModel, BaseQuerySet
from apps.core.storage import get_document_storage
from apps.referentiels.models import DateRange, fr

MATRICULE_PATTERN = r"^[A-Z0-9/.-]{1,20}$"
MATRICULE_HELP = "Lettres, chiffres, « / », « - » et « . », 20 caractères au plus."
MATRICULE_TAKEN = "Ce matricule est déjà attribué à un autre agent."
MATRICULE_FIXED = "Le matricule ne peut pas être modifié."
NEVER_DELETED = "Un agent n'est jamais supprimé : son matricule ne doit pas être réutilisé."
BIRTH_FUTURE = "La date de naissance ne peut pas être dans le futur."
EARLIEST_BIRTH = date(1900, 1, 1)


class StatutAgent(models.TextChoices):
    """An agent's status at a date, computed from their contracts, never stored (agent
    list D1, D2). Milestone 3 adds Détaché, En disponibilité and Sorti, which take
    precedence over En activité. The frontend mirrors this list."""

    ACTIF = "actif", "En activité"
    A_VENIR = "a_venir", "À venir"
    INACTIF = "inactif", "Sans contrat en cours"
    SANS_CONTRAT = "sans_contrat", "Sans contrat"


class AgentQuerySet(BaseQuerySet):
    def with_statut(self, jour: date) -> "AgentQuerySet":
        """Annotate `statut` on a day, in SQL, so the list can filter on it (agent list D3).

        Agent.statut_au() gives the same answer from prefetched contracts.
        """
        contrats = Contrat.objects.filter(agent=OuterRef("pk"))
        en_cours = contrats.filter(date_debut__lte=jour).filter(
            Q(date_fin__isnull=True) | Q(date_fin__gte=jour)
        )
        return self.annotate(
            statut=Case(
                When(Exists(en_cours), then=Value(StatutAgent.ACTIF)),
                When(
                    Exists(contrats.filter(date_debut__lte=jour)), then=Value(StatutAgent.INACTIF)
                ),
                When(Exists(contrats.filter(date_debut__gt=jour)), then=Value(StatutAgent.A_VENIR)),
                default=Value(StatutAgent.SANS_CONTRAT),
                output_field=models.CharField(),
            )
        )


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

    objects = AgentQuerySet.as_manager()

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

    def _prefetched(self, name: str):
        """The rows of a relation prefetched with the agent, or None when not prefetched."""
        return getattr(self, "_prefetched_objects_cache", {}).get(name)

    @property
    def date_engagement(self) -> date | None:
        """The start of the agent's first contract, never stored (contract D10)."""
        if self.pk is None:
            return None
        prefetched = self._prefetched("contrats")
        if prefetched is not None:
            return min((c.date_debut for c in prefetched), default=None)
        return self.contrats.aggregate(debut=Min("date_debut"))["debut"]

    def contrat_au(self, jour: date) -> "Contrat | None":
        """The contract in force on a day, or None (contract D11)."""
        if self.pk is None:
            return None
        prefetched = self._prefetched("contrats")
        if prefetched is not None:
            return next((c for c in prefetched if c.en_vigueur(jour)), None)
        return (
            self.contrats.filter(date_debut__lte=jour)
            .filter(Q(date_fin__isnull=True) | Q(date_fin__gte=jour))
            .first()
        )

    def _au(self, name: str, jour: date):
        """The row of a start-dated history in force on a day: the latest one
        dated on or before it (position history D2, D12)."""
        if self.pk is None:
            return None
        prefetched = self._prefetched(name)
        if prefetched is not None:
            dated = [row for row in prefetched if row.date_effet <= jour]
            return max(dated, key=lambda row: row.date_effet, default=None)
        return getattr(self, name).filter(date_effet__lte=jour).order_by("-date_effet").first()

    def statut_au(self, jour: date) -> str:
        """The agent's status on a day (agent list D1), from prefetched contracts when
        present; the same rule as AgentQuerySet.with_statut()."""
        prefetched = self._prefetched("contrats")
        contrats = list(prefetched) if prefetched is not None else list(self.contrats.all())
        if any(c.en_vigueur(jour) for c in contrats):
            return StatutAgent.ACTIF
        if any(c.date_debut <= jour for c in contrats):
            return StatutAgent.INACTIF
        if contrats:
            return StatutAgent.A_VENIR
        return StatutAgent.SANS_CONTRAT

    def affectation_au(self, jour: date) -> "Affectation | None":
        """The assignment in force on a day, or None (position history D12)."""
        return self._au("affectations", jour)

    def classement_au(self, jour: date) -> "Classement | None":
        """The classification in force on a day, or None (position history D12)."""
        return self._au("classements", jour)

    def compte_bancaire_au(self, jour: date) -> "CompteBancaire | None":
        """The bank account pay goes to on a day, or None (bank account D11)."""
        return self._au("comptes_bancaires", jour)

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


def ferme_le(reference, jour: date) -> bool:
    """Whether a dated reference row is closed on a day: open from date_ouverture
    included to date_fermeture excluded."""
    return reference.date_ouverture > jour or (
        reference.date_fermeture is not None and reference.date_fermeture <= jour
    )


def agent_change(row) -> bool:
    """Whether a saved row is being moved to another agent."""
    if row.pk is None:
        return False
    old = type(row)._base_manager.filter(pk=row.pk).values_list("agent_id", flat=True).first()
    return old is not None and old != row.agent_id


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
    pieces_jointes = GenericRelation(
        "agents.PieceJointe", content_type_field="content_type", object_id_field="objet_id"
    )  # documents on events D6

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

    @property
    def evenement(self) -> str | None:
        """The event kind of this row, from the agent's history (documents on events D7)."""
        from .evenements import evenement_de

        return evenement_de(self).evenement

    @property
    def date_evenement(self) -> date:
        return self.date_debut

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
            if debut and ferme_le(type_contrat, debut):
                errors["type_contrat"] = [
                    f"Le type « {type_contrat.code} » n'est pas ouvert le {fr(debut)}."
                ]
            if type_contrat.duree_determinee and not fin:
                errors.setdefault("date_fin", []).append(FIN_OBLIGATOIRE)
            elif not type_contrat.duree_determinee and fin:
                errors.setdefault("date_fin", []).append(FIN_INTERDITE)
            if essai and not type_contrat.periode_essai:
                errors.setdefault("fin_periode_essai", []).append(ESSAI_INTERDIT)

        if agent_change(self):
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


HORS_CONTRAT = "L'agent n'est sous aucun contrat à cette date."
AFFECTATION_DATE_PRISE = "Cet agent a déjà une affectation à cette date."
AFFECTATION_AGENT_FIXED = "Une affectation ne peut pas passer à un autre agent."
AFFECTATION_NEVER_DELETED = "Une affectation n'est jamais supprimée : corrigez-la."
UNITE_FERMEE = "L'unité « {ref} » n'est pas ouverte le {jour}."
FONCTION_FERMEE = "La fonction « {ref} » n'est pas ouverte le {jour}."


def check_under_contract(row, errors: dict[str, list[str]]) -> None:
    """date_effet must fall inside one of the agent's contracts (position history D10).

    An agent not saved yet (the admin's add page) has no contract, so the row is
    refused on its field rather than failing on save.
    """
    agent = getattr(row, "agent", None)
    if agent is not None and row.date_effet and agent.contrat_au(row.date_effet) is None:
        errors.setdefault("date_effet", []).append(HORS_CONTRAT)


def check_open(row, field: str, closed: str, label, errors: dict[str, list[str]]) -> None:
    """The reference in `field` must be open on date_effet (position history D9).
    `closed` is the message, with {ref} and {jour}; `label` names the reference."""
    if getattr(row, f"{field}_id") and row.date_effet:
        reference = getattr(row, field)
        if ferme_le(reference, row.date_effet):
            errors.setdefault(field, []).append(
                closed.format(ref=label(reference), jour=fr(row.date_effet))
            )


class Affectation(BaseModel):
    """Where an agent works and in which function, from a date (position history
    D1 to D3, D5, D6).

    Only the effective date is stored: a row applies until the agent's next row
    (D2). The entry date is date_creation (D8).
    """

    module = "agents"

    agent = models.ForeignKey(
        Agent, verbose_name="agent", on_delete=models.PROTECT, related_name="affectations"
    )
    unite = models.ForeignKey(
        "referentiels.UniteOrganisationnelle",
        verbose_name="unité",
        on_delete=models.PROTECT,
        related_name="+",
    )
    fonction = models.ForeignKey(
        "referentiels.Fonction",
        verbose_name="fonction",
        on_delete=models.PROTECT,
        related_name="+",
    )
    date_effet = models.DateField(
        "date d'effet",
        help_text="Premier jour où l'affectation s'applique ; elle court jusqu'à la suivante.",
    )
    pieces_jointes = GenericRelation(
        "agents.PieceJointe", content_type_field="content_type", object_id_field="objet_id"
    )  # documents on events D6

    class Meta:
        verbose_name = "affectation"
        verbose_name_plural = "affectations"
        ordering = ["agent", "date_effet"]  # D7
        default_permissions = NO_DELETE
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "date_effet"],
                name="affectation_une_par_date",
                violation_error_message=AFFECTATION_DATE_PRISE,
            ),
        ]

    def __str__(self):
        unite = self.unite.code if self.unite_id else "?"
        fonction = self.fonction.nom if self.fonction_id else "?"
        matricule = self.agent.matricule if self.agent_id else "?"
        debut = fr(self.date_effet) if self.date_effet else "?"
        return f"{unite} · {fonction} depuis le {debut} — {matricule}"

    @property
    def evenement(self) -> str | None:
        """The event kind of this row, from the agent's history (documents on events D7)."""
        from .evenements import evenement_de

        return evenement_de(self).evenement

    @property
    def date_evenement(self) -> date:
        return self.date_effet

    def check_rules(self) -> None:
        """References open on the date, date under contract, agent fixed (D9, D10, D14)."""
        errors: dict[str, list[str]] = {}
        check_open(self, "unite", UNITE_FERMEE, lambda unite: unite.code, errors)
        check_open(self, "fonction", FONCTION_FERMEE, lambda fonction: fonction.code, errors)
        check_under_contract(self, errors)
        if agent_change(self):
            errors["agent"] = [AFFECTATION_AGENT_FIXED]
        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        self.check_rules()

    def save(self, **kwargs):
        self.check_rules()
        super().save(**kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(AFFECTATION_NEVER_DELETED)


CLASSEMENT_DATE_PRISE = "Cet agent a déjà un classement à cette date."
CLASSEMENT_AGENT_FIXED = "Un classement ne peut pas passer à un autre agent."
CLASSEMENT_NEVER_DELETED = "Un classement n'est jamais supprimé : corrigez-le."
ECHELON_FERME = "L'échelon « {ref} » n'est pas ouvert le {jour}."


class Classement(BaseModel):
    """An agent's grade and échelon, from a date (position history D1, D2, D4, D6).

    Only the échelon is stored; its grade and catégorie are read through it, so
    an échelon of another grade cannot be recorded (D4). A row applies until the
    agent's next row (D2).
    """

    module = "agents"

    agent = models.ForeignKey(
        Agent, verbose_name="agent", on_delete=models.PROTECT, related_name="classements"
    )
    echelon = models.ForeignKey(
        "referentiels.Echelon",
        verbose_name="échelon",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Le grade est celui de l'échelon.",
    )
    date_effet = models.DateField(
        "date d'effet",
        help_text="Premier jour où le classement s'applique ; il court jusqu'au suivant.",
    )
    pieces_jointes = GenericRelation(
        "agents.PieceJointe", content_type_field="content_type", object_id_field="objet_id"
    )  # documents on events D6

    class Meta:
        verbose_name = "classement"
        verbose_name_plural = "classements"
        ordering = ["agent", "date_effet"]  # D7
        default_permissions = NO_DELETE
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "date_effet"],
                name="classement_un_par_date",
                violation_error_message=CLASSEMENT_DATE_PRISE,
            ),
        ]

    def __str__(self):
        echelon = str(self.echelon) if self.echelon_id else "?"
        matricule = self.agent.matricule if self.agent_id else "?"
        debut = fr(self.date_effet) if self.date_effet else "?"
        return f"{echelon} depuis le {debut} — {matricule}"

    @property
    def grade(self):
        return self.echelon.grade

    @property
    def evenement(self) -> str | None:
        """The event kind of this row, from the agent's history (documents on events D7)."""
        from .evenements import evenement_de

        return evenement_de(self).evenement

    @property
    def date_evenement(self) -> date:
        return self.date_effet

    def check_rules(self) -> None:
        """Échelon open on the date, date under contract, agent fixed (D9, D10, D14).

        An échelon opens and closes within its grade, so an open échelon has an
        open grade.
        """
        errors: dict[str, list[str]] = {}
        check_open(self, "echelon", ECHELON_FERME, str, errors)
        check_under_contract(self, errors)
        if agent_change(self):
            errors["agent"] = [CLASSEMENT_AGENT_FIXED]
        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        self.check_rules()

    def save(self, **kwargs):
        self.check_rules()
        super().save(**kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(CLASSEMENT_NEVER_DELETED)


# Capital letters, digits, spaces and dashes, 5 to 34 characters, starting and
# ending with a letter or digit (bank account D7, Q36). Python and PostgreSQL
# both read it.
NUMERO_PATTERN = r"^[A-Z0-9][A-Z0-9 -]{3,32}[A-Z0-9]$"
NUMERO_HELP = "Lettres, chiffres, espaces et tirets, de 5 à 34 caractères."
NUMERO_PRIS = "Ce numéro de compte appartient déjà à un autre agent dans cette banque."
COMPTE_DATE_PRISE = "Cet agent a déjà un compte bancaire à cette date."
COMPTE_AGENT_FIXED = "Un compte bancaire ne peut pas passer à un autre agent."
COMPTE_NEVER_DELETED = "Un compte bancaire n'est jamais supprimé : corrigez-le."
BANQUE_FERMEE = "La banque « {ref} » n'est pas ouverte le {jour}."


class CompteBancaire(BaseModel):
    """The bank account an agent is paid into, from a date (bank account D1 to D5).

    Only the effective date is stored: a row applies until the agent's next row
    (D2). A bank and number belong to one agent only (D8). Pay data: its audit
    entries are seen by the pay profiles only (D15).
    """

    module = "paie"

    agent = models.ForeignKey(
        Agent, verbose_name="agent", on_delete=models.PROTECT, related_name="comptes_bancaires"
    )
    banque = models.ForeignKey(
        "referentiels.Banque", verbose_name="banque", on_delete=models.PROTECT, related_name="+"
    )
    # Wider than the 34 allowed, so that the format rule alone reports a long number.
    numero = models.CharField("numéro de compte", max_length=40, help_text=NUMERO_HELP)
    date_effet = models.DateField(
        "date d'effet",
        help_text="Premier jour où la paie est versée sur ce compte ; il court jusqu'au suivant.",
    )

    class Meta:
        verbose_name = "compte bancaire"
        verbose_name_plural = "comptes bancaires"
        ordering = ["agent", "date_effet"]  # D5
        default_permissions = NO_DELETE
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "date_effet"],
                name="compte_bancaire_un_par_date",
                violation_error_message=COMPTE_DATE_PRISE,
            ),
            models.CheckConstraint(
                condition=Q(numero__regex=NUMERO_PATTERN),
                name="compte_bancaire_numero_valide",
                violation_error_message=NUMERO_HELP,
            ),
            ExclusionConstraint(
                name="compte_bancaire_un_seul_agent",
                expressions=[
                    ("banque", RangeOperators.EQUAL),
                    ("numero", RangeOperators.EQUAL),
                    ("agent", RangeOperators.NOT_EQUAL),
                ],
                violation_error_message=NUMERO_PRIS,
            ),
        ]

    def __str__(self):
        banque = self.banque.code if self.banque_id else "?"
        matricule = self.agent.matricule if self.agent_id else "?"
        debut = fr(self.date_effet) if self.date_effet else "?"
        return f"{banque} — {self.numero or '?'} depuis le {debut} — {matricule}"

    def normalise(self) -> None:
        if self.numero:
            self.numero = self.numero.strip().upper()

    def check_rules(self) -> None:
        """Number format and owner, bank open on the date, agent fixed (D7 to D9, D13)."""
        errors: dict[str, list[str]] = {}
        if self.numero:
            if not re.fullmatch(NUMERO_PATTERN, self.numero):
                errors["numero"] = [NUMERO_HELP]
            elif self.banque_id and self.agent_id:
                held = type(self)._base_manager.filter(banque_id=self.banque_id, numero=self.numero)
                if held.exclude(agent_id=self.agent_id).exists():
                    errors["numero"] = [NUMERO_PRIS]
        check_open(self, "banque", BANQUE_FERMEE, lambda banque: banque.code, errors)
        if agent_change(self):
            errors["agent"] = [COMPTE_AGENT_FIXED]
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
        raise PermissionError(COMPTE_NEVER_DELETED)


# Scanned supporting documents (document storage D1 to D6, D11, D17).
DOCUMENT_TYPES_MIME = (
    ("application/pdf", "PDF"),
    ("image/jpeg", "JPEG"),
    ("image/png", "PNG"),
)
TYPE_DOCUMENT_FERME = "Le type de pièce « {ref} » n'est pas ouvert le {jour}."
DOCUMENT_FIXE = "Une pièce déposée ne peut pas être modifiée : retirez-la et déposez-la à nouveau."
DOCUMENT_DOUBLON = "Ce fichier est déjà déposé pour cet agent avec ce type de pièce."
DOCUMENT_NEVER_DELETED = "Une pièce n'est jamais supprimée : retirez-la."
DEJA_RETIRE = "Cette pièce est déjà retirée."
MOTIF_COURT = "Indiquez le motif du retrait, en 10 caractères au moins."
RETRAIT_INCOHERENT = "Une pièce retirée a un motif et une date de retrait ; une autre n'en a pas."
MOTIF_MIN = 10
# Fields set at upload, never changed afterwards (D2).
DOCUMENT_FIXED_FIELDS = (
    "agent_id", "type_document_id", "fichier", "nom_original", "type_mime", "taille",
    "empreinte", "date_document",
)  # fmt: skip


def chemin_document(instance, filename) -> str:
    """documents/<yyyy>/<mm>/<uuid>, never the original name (D4)."""
    now = timezone.now()
    return f"documents/{now:%Y}/{now:%m}/{uuid.uuid4().hex}"


class DocumentQuerySet(BaseQuerySet):
    def lisibles_par(self, user) -> "DocumentQuerySet":
        """Documents a user may read: any non-confidential type, a confidential one
        only through one of its groups; everything for a superuser (D14)."""
        if user.is_superuser:
            return self
        return self.filter(
            Q(type_document__confidentiel=False)
            | Q(type_document__groupes_autorises__in=user.groups.all())
        ).distinct()


class Document(BaseModel):
    """One scanned supporting document of an agent's file (document storage D1).

    The file is encrypted on disk (D7); the row keeps what was checked at upload,
    which never changes (D2). A wrong upload is retired with a reason, never
    deleted (D17). Phase 2.7 links events to these rows.
    """

    module = "agents"

    agent = models.ForeignKey(
        Agent, verbose_name="agent", on_delete=models.PROTECT, related_name="documents"
    )
    type_document = models.ForeignKey(
        "referentiels.TypeDocument",
        verbose_name="type de pièce",
        on_delete=models.PROTECT,
        related_name="+",
    )
    fichier = models.FileField(
        "fichier", storage=get_document_storage, upload_to=chemin_document, max_length=100
    )
    nom_original = models.CharField("nom du fichier déposé", max_length=150)
    type_mime = models.CharField("format", max_length=30, choices=DOCUMENT_TYPES_MIME)
    taille = models.PositiveIntegerField("taille (octets)")
    empreinte = models.CharField("empreinte SHA-256", max_length=64)
    date_document = models.DateField(
        "date de la pièce", null=True, blank=True, help_text="La date imprimée sur la pièce."
    )
    retire = models.BooleanField("retirée", default=False)
    motif_retrait = models.TextField("motif du retrait", blank=True)
    date_retrait = models.DateTimeField("date du retrait", null=True, blank=True)
    retire_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="retirée par",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    objects = DocumentQuerySet.as_manager()

    class Meta:
        verbose_name = "pièce justificative"
        verbose_name_plural = "pièces justificatives"
        ordering = ["agent", "-date_creation", "-id"]  # D5
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(type_mime__in=[value for value, _ in DOCUMENT_TYPES_MIME]),
                name="document_format_valide",
                violation_error_message="Format refusé : PDF, JPEG ou PNG seulement.",
            ),
            models.CheckConstraint(
                condition=Q(taille__gt=0),
                name="document_non_vide",
                violation_error_message="Le fichier est vide.",
            ),
            models.CheckConstraint(
                condition=Q(empreinte__regex=r"^[0-9a-f]{64}$"),
                name="document_empreinte_valide",
                violation_error_message="Empreinte invalide.",
            ),
            models.CheckConstraint(
                condition=Q(
                    retire=False,
                    motif_retrait="",
                    date_retrait__isnull=True,
                    retire_par__isnull=True,
                )
                | Q(retire=True, motif_retrait__regex=r"\S", date_retrait__isnull=False),
                name="document_retrait_coherent",
                violation_error_message=RETRAIT_INCOHERENT,
            ),  # fmt: skip
            models.UniqueConstraint(
                fields=["agent", "type_document", "empreinte"],
                condition=Q(retire=False),
                name="document_sans_doublon",
                violation_error_message=DOCUMENT_DOUBLON,
            ),
        ]

    def __str__(self):
        code = self.type_document.code if self.type_document_id else "?"
        matricule = self.agent.matricule if self.agent_id else "?"
        return f"{code} — {self.nom_original or '?'} — {matricule}"

    def check_rules(self) -> None:
        """Type open on the upload day; nothing but the retirement changes (D2, D3)."""
        errors: dict[str, list[str]] = {}
        if self.pk is None:
            if self.type_document_id:
                jour = timezone.localdate()
                if ferme_le(self.type_document, jour):
                    errors["type_document"] = [
                        TYPE_DOCUMENT_FERME.format(ref=self.type_document.code, jour=fr(jour))
                    ]
        else:
            old = type(self)._base_manager.filter(pk=self.pk).values(*DOCUMENT_FIXED_FIELDS).first()
            if old is not None:
                for name in DOCUMENT_FIXED_FIELDS:
                    current = getattr(self, name)
                    if name == "fichier":
                        current = current.name
                    if old[name] != current:
                        errors.setdefault(name.removesuffix("_id"), []).append(DOCUMENT_FIXE)
        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        self.check_rules()

    def save(self, **kwargs):
        self.check_rules()
        super().save(**kwargs)

    def retirer(self, motif: str, auteur=None) -> None:
        """Retire a wrong upload once, with its reason; the file is kept (D17)."""
        if self.retire:
            raise ValidationError({"motif": [DEJA_RETIRE]})
        motif = (motif or "").strip()
        if len(motif) < MOTIF_MIN:
            raise ValidationError({"motif": [MOTIF_COURT]})
        self.retire = True
        self.motif_retrait = motif
        self.date_retrait = timezone.now()
        self.retire_par = auteur
        self.modifie_par = auteur
        self.save()

    def delete(self, *args, **kwargs):
        raise PermissionError(DOCUMENT_NEVER_DELETED)


# Documents attached to the events they justify (documents on events D1 to D5).
# The event models wired so far; later phases add theirs (D7).
MODELES_EVENEMENT = ("contrat", "affectation", "classement")
LIEN_DOUBLON = "Cette pièce est déjà jointe à cet événement."
LIEN_AUTRE_AGENT = "Cette pièce appartient au dossier d'un autre agent."
LIEN_PIECE_RETIREE = "Une pièce retirée ne peut pas être jointe."
LIEN_EVENEMENT_INCONNU = "Cet enregistrement n'est pas un événement qui porte des pièces."
LIEN_FIXE = "Un lien ne peut pas être modifié : retirez-le et joignez la bonne pièce."
LIEN_DEJA_RETIRE = "Ce lien est déjà retiré."
LIEN_NEVER_DELETED = "Un lien n'est jamais supprimé : retirez-le."


class PieceJointe(BaseModel):
    """A document of the agent's file attached to one of their events (documents on
    events D1 to D5).

    The event is any model of MODELES_EVENEMENT, through a generic key; one
    document can justify several events. A wrong link is removed (date_retrait),
    never deleted (D4); only active links count (D14).
    """

    module = "agents"

    document = models.ForeignKey(
        Document, verbose_name="pièce", on_delete=models.PROTECT, related_name="liens"
    )
    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        verbose_name="type d'événement",
        on_delete=models.PROTECT,
        related_name="+",
    )
    objet_id = models.PositiveBigIntegerField("événement")
    evenement_objet = GenericForeignKey("content_type", "objet_id")
    date_retrait = models.DateTimeField("date du retrait", null=True, blank=True)
    retire_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="retiré par",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "pièce jointe à un événement"
        verbose_name_plural = "pièces jointes aux événements"
        ordering = ["content_type", "objet_id", "date_creation", "id"]
        default_permissions = NO_DELETE
        indexes = [models.Index(fields=["content_type", "objet_id"], name="piecejointe_evenement")]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "content_type", "objet_id"],
                condition=Q(date_retrait__isnull=True),
                name="piecejointe_un_lien_actif",
                violation_error_message=LIEN_DOUBLON,
            ),
            models.CheckConstraint(
                condition=Q(retire_par__isnull=True) | Q(date_retrait__isnull=False),
                name="piecejointe_retrait_date",
                violation_error_message="Un lien retiré a une date de retrait.",
            ),
        ]

    def __str__(self):
        if self.document_id:
            piece = f"{self.document.type_document.code} — {self.document.nom_original}"
        else:
            piece = "?"
        evenement = self.evenement_objet if self.content_type_id and self.objet_id else "?"
        return f"{piece} → {evenement}"

    @property
    def actif(self) -> bool:
        return self.date_retrait is None

    def check_rules(self) -> None:
        """Event of a known model and of the document's agent, document not retired, no
        duplicate active link; nothing changes once saved but the removal (D2 to D4)."""
        errors: dict[str, list[str]] = {}
        if self.pk is None:
            if self.content_type_id and (
                self.content_type.app_label != "agents"
                or self.content_type.model not in MODELES_EVENEMENT
            ):
                errors["content_type"] = [LIEN_EVENEMENT_INCONNU]
            elif self.content_type_id and self.objet_id:
                evenement = self.evenement_objet
                if evenement is None:
                    errors["objet_id"] = [LIEN_EVENEMENT_INCONNU]
                elif self.document_id and evenement.agent_id != self.document.agent_id:
                    errors["document"] = [LIEN_AUTRE_AGENT]
            if self.document_id and "document" not in errors:
                if self.document.retire:
                    errors["document"] = [LIEN_PIECE_RETIREE]
                elif (
                    self.content_type_id
                    and self.objet_id
                    and type(self)
                    ._base_manager.filter(
                        document_id=self.document_id,
                        content_type_id=self.content_type_id,
                        objet_id=self.objet_id,
                        date_retrait__isnull=True,
                    )
                    .exists()
                ):
                    errors["document"] = [LIEN_DOUBLON]
        else:
            old = (
                type(self)
                ._base_manager.filter(pk=self.pk)
                .values("document_id", "content_type_id", "objet_id")
                .first()
            )
            if old is not None:
                for name, value in old.items():
                    if getattr(self, name) != value:
                        errors.setdefault(name.removesuffix("_id"), []).append(LIEN_FIXE)
        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        self.check_rules()

    def save(self, **kwargs):
        self.check_rules()
        super().save(**kwargs)

    def retirer(self, auteur=None) -> None:
        """Remove the link once; the row and the document stay (D4)."""
        if self.date_retrait is not None:
            raise ValidationError({"lien": [LIEN_DEJA_RETIRE]})
        self.date_retrait = timezone.now()
        self.retire_par = auteur
        self.modifie_par = auteur
        self.save()

    def delete(self, *args, **kwargs):
        raise PermissionError(LIEN_NEVER_DELETED)
