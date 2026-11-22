"""Hiring an agent in one go (agent creation form D1 to D5, D9).

One request creates the agent, their contact details (when given), their first
contract and their first assignment and classification, dated on the contract's
start, in one transaction. The rules are the models' own: every section is checked,
and all errors come back together, nested by section; any error creates nothing.
"""

import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.permissions import BasePermission

from apps.referentiels.edition import as_drf_errors
from apps.referentiels.models import Echelon, Fonction, TypeContrat, UniteOrganisationnelle

from .models import Affectation, Agent, Classement, Contrat, Coordonnees

IDENTITE = ("matricule", "nom", "postnom", "prenom", "sexe", "date_naissance",
            "lieu_naissance", "nationalite")  # fmt: skip
COORDONNEES = ("adresse", "commune", "ville", "telephone", "telephone_secondaire", "courriel",
               "urgence_nom", "urgence_lien", "urgence_telephone")  # fmt: skip
PERMISSIONS = ("agents.add_agent", "agents.add_contrat", "agents.add_affectation",
               "agents.add_classement")  # fmt: skip


class CoordonneesSection(serializers.Serializer):
    adresse = serializers.CharField(allow_blank=True, required=False, default="")
    commune = serializers.CharField(allow_blank=True, required=False, default="")
    ville = serializers.CharField(allow_blank=True, required=False, default="")
    telephone = serializers.CharField(allow_blank=True, required=False, default="")
    telephone_secondaire = serializers.CharField(allow_blank=True, required=False, default="")
    courriel = serializers.CharField(allow_blank=True, required=False, default="")
    urgence_nom = serializers.CharField(allow_blank=True, required=False, default="")
    urgence_lien = serializers.CharField(allow_blank=True, required=False, default="")
    urgence_telephone = serializers.CharField(allow_blank=True, required=False, default="")


class ContratSection(serializers.Serializer):
    type_contrat = serializers.PrimaryKeyRelatedField(queryset=TypeContrat.objects.all())
    date_debut = serializers.DateField()
    date_fin = serializers.DateField(required=False, allow_null=True, default=None)
    fin_periode_essai = serializers.DateField(required=False, allow_null=True, default=None)


class AffectationSection(serializers.Serializer):
    unite = serializers.PrimaryKeyRelatedField(queryset=UniteOrganisationnelle.objects.all())
    fonction = serializers.PrimaryKeyRelatedField(queryset=Fonction.objects.all())


class ClassementSection(serializers.Serializer):
    echelon = serializers.PrimaryKeyRelatedField(queryset=Echelon.objects.all())


class EngagementSerializer(serializers.Serializer):
    """The hiring request: identity at the top, the other parts as sections (D1)."""

    matricule = serializers.CharField(allow_blank=True)
    nom = serializers.CharField(allow_blank=True)
    postnom = serializers.CharField(allow_blank=True, required=False, default="")
    prenom = serializers.CharField(allow_blank=True, required=False, default="")
    sexe = serializers.CharField(allow_blank=True)
    date_naissance = serializers.DateField()
    lieu_naissance = serializers.CharField(allow_blank=True)
    nationalite = serializers.CharField(allow_blank=True, required=False, default="Congolaise")
    coordonnees = CoordonneesSection(required=False, allow_null=True, default=None)
    contrat = ContratSection()
    affectation = AffectationSection()
    classement = ClassementSection()


def coordonnees_saisies(data: dict | None) -> bool:
    """Contact details are created only when something was typed (D1)."""
    return bool(data) and any((data.get(name) or "").strip() for name in COORDONNEES)


class EngagementPermission(BasePermission):
    """Hiring needs the add permissions of every part it creates (D9)."""

    message = "Vous ne pouvez pas engager d'agent."

    def has_permission(self, request, view):
        if getattr(view, "action", None) not in ("create", "matricule_suivant", "doublons"):
            return True
        user = request.user
        if view.action != "create":
            return user.has_perm("agents.add_agent")
        needed = list(PERMISSIONS)
        if coordonnees_saisies(
            request.data.get("coordonnees") if hasattr(request.data, "get") else None
        ):
            needed.append("agents.add_coordonnees")
        return all(user.has_perm(name) for name in needed)


def _check(row, errors: dict, section: str | None, save: bool) -> bool:
    """full_clean() then save a row; its errors go under `section` (top level when None).
    A row whose agent is not saved is only checked, its agent left out."""
    exclude = [] if save else ["agent"]
    try:
        row.full_clean(exclude=exclude)
        if save:
            row.save()
        return True
    except DjangoValidationError as error:
        found = as_drf_errors(error)
        if section is None:
            errors.update(found)
        else:
            errors.setdefault(section, {}).update(found)
        return False


def engager(data: dict, auteur) -> Agent:
    """Create the hiring's rows, or none (D2 to D4); raises a DRF ValidationError
    holding every error, nested by section."""
    errors: dict = {}
    authors = {"cree_par": auteur, "modifie_par": auteur}
    with transaction.atomic():
        agent = Agent(**{name: data[name] for name in IDENTITE}, **authors)
        saved = _check(agent, errors, None, save=True)

        coordonnees = data.get("coordonnees")
        if coordonnees_saisies(coordonnees):
            row = Coordonnees(agent=agent if saved else None, **coordonnees, **authors)
            _check(row, errors, "coordonnees", save=saved)

        contrat = data["contrat"]
        debut = contrat["date_debut"]
        contrat_ok = _check(
            Contrat(agent=agent if saved else None, **contrat, **authors),
            errors, "contrat", save=saved,
        )  # fmt: skip
        positions = saved and contrat_ok  # the positions' rules read the saved contract
        affectation = data["affectation"]
        _check(
            Affectation(agent=agent if positions else None, date_effet=debut, **affectation,
                        **authors),
            errors, "affectation", save=positions,
        )  # fmt: skip
        _check(
            Classement(agent=agent if positions else None, date_effet=debut,
                       echelon=data["classement"]["echelon"], **authors),
            errors, "classement", save=positions,
        )  # fmt: skip
        if errors:
            raise serializers.ValidationError(errors)  # leaving atomic() rolls everything back
    return agent


SUGGESTION = re.compile(r"^ARPTC/(\d+)/\d{4}$")
DOUBLONS_MAX = 10


class AnneeSerializer(serializers.Serializer):
    annee = serializers.IntegerField(min_value=1900, max_value=2100)


def matricule_suivant(annee: int) -> str:
    """ARPTC/<n>/<year>, n one more than the highest sequence of the bulletin-shaped
    matricules, padded to 4 digits (D6). Other shapes are ignored."""
    highest = 0
    for matricule in Agent.objects.filter(matricule__startswith="ARPTC/").values_list(
        "matricule", flat=True
    ):
        match = SUGGESTION.match(matricule)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"ARPTC/{highest + 1:04d}/{annee}"


class DoublonsSerializer(serializers.Serializer):
    nom = serializers.CharField()
    postnom = serializers.CharField(required=False, allow_blank=True)
    prenom = serializers.CharField(required=False, allow_blank=True)
    date_naissance = serializers.DateField()


def doublons(params: dict):
    """Agents with the same nom (case and accents ignored) and birth date, and the same
    prénom when given (D7)."""
    from .recherche import sans_accents

    queryset = Agent.objects.filter(
        nom__unaccent__iexact=sans_accents(params["nom"].strip()),
        date_naissance=params["date_naissance"],
    )
    prenom = (params.get("prenom") or "").strip()
    if prenom:
        queryset = queryset.filter(prenom__unaccent__iexact=sans_accents(prenom))
    return queryset.order_by("nom", "postnom", "prenom", "matricule")[:DOUBLONS_MAX]
