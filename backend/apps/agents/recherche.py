"""Searching the agents (agent list D4 to D10).

Every filter runs in SQL, at a date: the status from the contracts (D1, D3), the
unit, function and grade from the assignment and classification in force that day
(D6). The text matches the matricule or the names, ignoring case and accents (D5).
"""

import unicodedata
from datetime import date

from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.utils import timezone
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination

from apps.referentiels.models import Fonction, Grade, UniteOrganisationnelle

from .models import Affectation, Agent, Classement, StatutAgent

TAILLE_MAX = 100
STATUT_INCONNU = "Statut inconnu : {valeur}. Valeurs possibles : {valeurs}."


def sans_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def sous_unites(unite_id: int) -> set[int]:
    """The unit and every unit below it, open or closed (an assignment may point to a
    unit closed since)."""
    enfants: dict[int | None, list[int]] = {}
    for pk, parent in UniteOrganisationnelle.objects.values_list("pk", "parent_id"):
        enfants.setdefault(parent, []).append(pk)
    found, todo = set(), [unite_id]
    while todo:
        pk = todo.pop()
        if pk not in found:
            found.add(pk)
            todo.extend(enfants.get(pk, []))
    return found


class RechercheSerializer(serializers.Serializer):
    """The query parameters of /api/agents/ (D4, D10), each refused with a French
    message on its own name."""

    q = serializers.CharField(required=False, allow_blank=True, max_length=100)
    unite = serializers.PrimaryKeyRelatedField(
        queryset=UniteOrganisationnelle.objects.all(), required=False
    )
    grade = serializers.PrimaryKeyRelatedField(queryset=Grade.objects.all(), required=False)
    fonction = serializers.PrimaryKeyRelatedField(queryset=Fonction.objects.all(), required=False)
    statut = serializers.CharField(required=False, allow_blank=True)
    date = serializers.DateField(required=False)
    tri = serializers.ChoiceField(choices=["nom", "matricule"], required=False, default="nom")
    taille = serializers.IntegerField(required=False, min_value=1, max_value=TAILLE_MAX)

    def validate_statut(self, value: str) -> list[str]:
        codes = [code.strip() for code in value.split(",") if code.strip()]
        unknown = [code for code in codes if code not in StatutAgent.values]
        if unknown:
            raise serializers.ValidationError(
                STATUT_INCONNU.format(
                    valeur=", ".join(unknown), valeurs=", ".join(StatutAgent.values)
                )
            )
        return codes

    def validate(self, attrs):
        attrs.setdefault("date", timezone.localdate())
        return attrs


def rechercher(params: dict) -> QuerySet[Agent]:
    """The agents matching validated parameters, with `statut` annotated on their date."""
    jour: date = params["date"]
    queryset = Agent.objects.with_statut(jour)

    for word in sans_accents(params.get("q") or "").split():
        queryset = queryset.filter(
            Q(matricule__icontains=word)
            | Q(nom__unaccent__icontains=word)
            | Q(postnom__unaccent__icontains=word)
            | Q(prenom__unaccent__icontains=word)
        )

    if params.get("unite") or params.get("fonction"):
        affectation = Affectation.objects.filter(
            agent=OuterRef("pk"), date_effet__lte=jour
        ).order_by("-date_effet")
        queryset = queryset.annotate(
            unite_au=Subquery(affectation.values("unite_id")[:1]),
            fonction_au=Subquery(affectation.values("fonction_id")[:1]),
        )
        if params.get("unite"):
            queryset = queryset.filter(unite_au__in=sous_unites(params["unite"].pk))
        if params.get("fonction"):
            queryset = queryset.filter(fonction_au=params["fonction"].pk)

    if params.get("grade"):
        classement = Classement.objects.filter(agent=OuterRef("pk"), date_effet__lte=jour).order_by(
            "-date_effet"
        )
        queryset = queryset.annotate(
            grade_au=Subquery(classement.values("echelon__grade_id")[:1])
        ).filter(grade_au=params["grade"].pk)

    if params.get("statut"):
        queryset = queryset.filter(statut__in=params["statut"])

    if params.get("tri") == "matricule":
        return queryset.order_by("matricule")
    return queryset.order_by("nom", "postnom", "prenom", "matricule")


class AgentPagination(PageNumberPagination):
    """25 agents a page, up to 100 with ?taille= (D8)."""

    page_size = 25
    page_size_query_param = "taille"
    max_page_size = TAILLE_MAX
