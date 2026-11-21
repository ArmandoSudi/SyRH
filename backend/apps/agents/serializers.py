from rest_framework import serializers

from apps.core.models import BASE_FIELDS
from apps.core.serializers import BaseModelSerializer

from .models import Affectation, Agent, Classement, Contrat, Coordonnees

AFFECTATION_FIELDS = [
    "id",
    "unite",
    "unite_code",
    "unite_nom",
    "unite_type",
    "fonction",
    "fonction_code",
    "fonction_nom",
    "date_effet",
]
CLASSEMENT_FIELDS = [
    "id",
    "echelon",
    "echelon_numero",
    "grade",
    "grade_code",
    "grade_nom",
    "categorie_code",
    "date_effet",
]


class AffectationSerializer(BaseModelSerializer):
    """One of an agent's assignments, with its unit and function (position history D19)."""

    unite_code = serializers.CharField(source="unite.code", read_only=True)
    unite_nom = serializers.CharField(source="unite.nom", read_only=True)
    unite_type = serializers.CharField(source="unite.type", read_only=True)
    fonction_code = serializers.CharField(source="fonction.code", read_only=True)
    fonction_nom = serializers.CharField(source="fonction.nom", read_only=True)

    class Meta:
        model = Affectation
        fields = [*AFFECTATION_FIELDS, *BASE_FIELDS]


class AffectationActuelleSerializer(AffectationSerializer):
    """The assignment in force today, without the base fields (position history D20)."""

    class Meta(AffectationSerializer.Meta):
        fields = AFFECTATION_FIELDS


class ClassementSerializer(BaseModelSerializer):
    """One of an agent's classifications, with the grade and catégorie of its échelon
    (position history D4, D19)."""

    echelon_numero = serializers.IntegerField(source="echelon.numero", read_only=True)
    grade = serializers.IntegerField(source="echelon.grade_id", read_only=True)
    grade_code = serializers.CharField(source="echelon.grade.code", read_only=True)
    grade_nom = serializers.CharField(source="echelon.grade.nom", read_only=True)
    categorie_code = serializers.CharField(source="echelon.grade.categorie.code", read_only=True)

    class Meta:
        model = Classement
        fields = [*CLASSEMENT_FIELDS, *BASE_FIELDS]


class ClassementActuelSerializer(ClassementSerializer):
    """The classification in force today, without the base fields (position history D20)."""

    class Meta(ClassementSerializer.Meta):
        fields = CLASSEMENT_FIELDS


class AgentSerializer(BaseModelSerializer):
    """An agent's identity, with the label of their sex (agent identity D19), and
    the assignment and classification in force today, or null (position history D20).

    Today comes from the context ("aujourdhui"), set once per request by the view;
    the rows are read from the prefetched histories.
    """

    sexe_libelle = serializers.CharField(source="get_sexe_display", read_only=True)
    affectation_actuelle = serializers.SerializerMethodField()
    classement_actuel = serializers.SerializerMethodField()

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
            "affectation_actuelle",
            "classement_actuel",
            *BASE_FIELDS,
        ]

    def get_affectation_actuelle(self, agent):
        row = agent.affectation_au(self.context["aujourdhui"])
        return AffectationActuelleSerializer(row).data if row else None

    def get_classement_actuel(self, agent):
        row = agent.classement_au(self.context["aujourdhui"])
        return ClassementActuelSerializer(row).data if row else None


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
    details D18), their hiring date and contracts in date order (contract D19), and
    their assignments and classifications in date order (position history D19)."""

    coordonnees = serializers.SerializerMethodField()
    date_engagement = serializers.DateField(read_only=True)
    contrats = ContratSerializer(many=True, read_only=True)
    affectations = AffectationSerializer(many=True, read_only=True)
    classements = ClassementSerializer(many=True, read_only=True)

    class Meta(AgentSerializer.Meta):
        fields = [
            *AgentSerializer.Meta.fields,
            "coordonnees",
            "date_engagement",
            "contrats",
            "affectations",
            "classements",
        ]

    def get_coordonnees(self, agent):
        try:
            coordonnees = agent.coordonnees
        except Coordonnees.DoesNotExist:
            return None
        return CoordonneesSerializer(coordonnees, context=self.context).data
