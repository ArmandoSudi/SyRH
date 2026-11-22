from rest_framework import serializers

from apps.core.models import BASE_FIELDS
from apps.core.serializers import BaseModelSerializer
from apps.referentiels.models import TypeDocument

from .models import (
    Affectation,
    Agent,
    Classement,
    CompteBancaire,
    Contrat,
    Coordonnees,
    Document,
    StatutAgent,
)

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
    statut = serializers.SerializerMethodField()
    statut_libelle = serializers.SerializerMethodField()
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
            "statut",
            "statut_libelle",
            "affectation_actuelle",
            "classement_actuel",
            *BASE_FIELDS,
        ]

    def get_statut(self, agent) -> str:
        """Annotated by the list's query; read from the contracts otherwise (agent list D9)."""
        statut = getattr(agent, "statut", None)
        return statut if statut is not None else agent.statut_au(self.context["aujourdhui"])

    def get_statut_libelle(self, agent) -> str:
        return StatutAgent(self.get_statut(agent)).label

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


COMPTE_BANCAIRE_FIELDS = ["id", "banque", "banque_code", "banque_nom", "numero", "date_effet"]


class CompteBancaireSerializer(BaseModelSerializer):
    """One of an agent's bank accounts, with its bank (bank account D18)."""

    banque_code = serializers.CharField(source="banque.code", read_only=True)
    banque_nom = serializers.CharField(source="banque.nom", read_only=True)

    class Meta:
        model = CompteBancaire
        fields = [*COMPTE_BANCAIRE_FIELDS, *BASE_FIELDS]


class CompteActuelSerializer(CompteBancaireSerializer):
    """The account pay goes to today, without the base fields (bank account D18)."""

    class Meta(CompteBancaireSerializer.Meta):
        fields = COMPTE_BANCAIRE_FIELDS


class ComptesBancairesSerializer(serializers.Serializer):
    """An agent's accounts in date order and the one in force today (bank account D18)."""

    comptes = CompteBancaireSerializer(source="comptes_bancaires", many=True, read_only=True)
    compte_actuel = serializers.SerializerMethodField()

    def get_compte_actuel(self, agent):
        row = agent.compte_bancaire_au(self.context["aujourdhui"])
        return CompteActuelSerializer(row).data if row else None


def nom_utilisateur(user) -> str | None:
    """A user as the screen shows them: full name, or the username without one."""
    if user is None:
        return None
    return user.get_full_name() or user.get_username()


class DocumentSerializer(BaseModelSerializer):
    """One scanned document, without its storage path or hash (document storage D20).

    The authors' names come with their ids, for the documents panel (D22).
    """

    type_document_code = serializers.CharField(source="type_document.code", read_only=True)
    type_document_nom = serializers.CharField(source="type_document.nom", read_only=True)
    confidentiel = serializers.BooleanField(source="type_document.confidentiel", read_only=True)
    cree_par_nom = serializers.SerializerMethodField()
    retire_par_nom = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "type_document",
            "type_document_code",
            "type_document_nom",
            "confidentiel",
            "nom_original",
            "type_mime",
            "taille",
            "date_document",
            "retire",
            "motif_retrait",
            "date_retrait",
            "retire_par",
            "retire_par_nom",
            "cree_par_nom",
            *BASE_FIELDS,
        ]
        read_only_fields = fields

    def get_cree_par_nom(self, obj) -> str | None:
        return nom_utilisateur(obj.cree_par)

    def get_retire_par_nom(self, obj) -> str | None:
        return nom_utilisateur(obj.retire_par)


class DocumentUploadSerializer(serializers.Serializer):
    """What a client sends to upload a document (document storage D18)."""

    type_document = serializers.PrimaryKeyRelatedField(queryset=TypeDocument.objects.all())
    fichier = serializers.FileField(
        allow_empty_file=True,  # create_document reports an empty file in its own words
        error_messages={"required": "Choisissez le fichier à déposer."},
    )
    date_document = serializers.DateField(required=False, allow_null=True)


class RetraitSerializer(serializers.Serializer):
    motif = serializers.CharField(allow_blank=True, trim_whitespace=True)


def piece_json(document, liens: dict[int, int]) -> dict:
    """A document as an event lists it, with the link that attaches it (documents on
    events D21)."""
    return {
        "id": document.pk,
        "lien": liens.get(document.pk),
        "nom_original": document.nom_original,
        "type_document_code": document.type_document.code,
        "type_mime": document.type_mime,
    }


def etat_json(etat) -> dict:
    """One event with its required pieces and status (documents on events D21)."""
    evenement = etat.evenement
    return {
        "cle": evenement.cle,
        "modele": evenement.modele,
        "id": evenement.objet.pk,
        "evenement": evenement.evenement,
        "evenement_libelle": evenement.evenement_libelle,
        "date": evenement.date.isoformat(),
        "libelle": evenement.libelle,
        "complet": etat.complet,
        "manquantes": etat.manquantes,
        "pieces": [
            {
                "code": piece.code,
                "nom": piece.nom,
                "obligatoire": piece.obligatoire,
                "satisfaite": piece.satisfaite,
                "documents": [piece_json(doc, etat.liens) for doc in piece.documents],
                "confidentielles": piece.confidentielles,
            }
            for piece in etat.pieces
        ],
        "autres": [piece_json(doc, etat.liens) for doc in etat.autres],
        "autres_confidentielles": etat.autres_confidentielles,
    }


class JoindreSerializer(serializers.Serializer):
    document = serializers.IntegerField(
        error_messages={"required": "Choisissez la pièce à joindre."}
    )
