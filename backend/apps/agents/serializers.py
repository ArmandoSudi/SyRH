from rest_framework import serializers

from apps.core.models import BASE_FIELDS
from apps.core.serializers import BaseModelSerializer

from .models import Agent, Coordonnees


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


class CoordonneesSerializer(BaseModelSerializer):
    """An agent's contact details (contact details D2, D18)."""

    class Meta:
        model = Coordonnees
        fields = [
            "adresse",
            "commune",
            "ville",
            "telephone",
            "telephone_secondaire",
            "courriel",
            "urgence_nom",
            "urgence_lien",
            "urgence_telephone",
            *BASE_FIELDS,
        ]


class AgentDetailSerializer(AgentSerializer):
    """One agent with their contact details, null when none were entered (contact
    details D18). The list keeps AgentSerializer."""

    coordonnees = serializers.SerializerMethodField()

    class Meta(AgentSerializer.Meta):
        fields = [*AgentSerializer.Meta.fields, "coordonnees"]

    def get_coordonnees(self, agent):
        try:
            coordonnees = agent.coordonnees
        except Coordonnees.DoesNotExist:
            return None
        return CoordonneesSerializer(coordonnees, context=self.context).data
