from rest_framework import serializers

from apps.core.models import BASE_FIELDS
from apps.core.serializers import BaseModelSerializer

from .models import Agent


class AgentSerializer(BaseModelSerializer):
    """An agent's identity, with the label of their sex (agent identity D19)."""

    sexe_libelle = serializers.CharField(source="get_sexe_display", read_only=True)

    class Meta:
        model = Agent
        fields = [
            "id",
            "matricule",
            "nom",
            "postnom",
            "prenom",
            "sexe",
            "sexe_libelle",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            *BASE_FIELDS,
        ]
