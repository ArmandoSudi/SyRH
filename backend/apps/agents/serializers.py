from rest_framework import serializers

from apps.core.models import BASE_FIELDS
from apps.core.serializers import BaseModelSerializer

from .models import Agent, Contrat, Coordonnees


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


class ContratSerializer(BaseModelSerializer):
    """One of an agent's contracts, with its type's code and name (contract D19)."""

    type_code = serializers.CharField(source="type_contrat.code", read_only=True)
    type_nom = serializers.CharField(source="type_contrat.nom", read_only=True)

    class Meta:
        model = Contrat
        fields = [
            "id",
            "type_contrat",
            "type_code",
            "type_nom",
            "date_debut",
            "date_fin",
            "fin_periode_essai",
            *BASE_FIELDS,
        ]


class AgentDetailSerializer(AgentSerializer):
    """One agent with their contact details, null when none were entered (contact
    details D18), their hiring date and contracts in date order (contract D19). The
    list keeps AgentSerializer."""

    coordonnees = serializers.SerializerMethodField()
    date_engagement = serializers.DateField(read_only=True)
    contrats = ContratSerializer(many=True, read_only=True)

    class Meta(AgentSerializer.Meta):
        fields = [*AgentSerializer.Meta.fields, "coordonnees", "date_engagement", "contrats"]

    def get_coordonnees(self, agent):
        try:
            coordonnees = agent.coordonnees
        except Coordonnees.DoesNotExist:
            return None
        return CoordonneesSerializer(coordonnees, context=self.context).data
