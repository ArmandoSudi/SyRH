from django.utils import timezone
from rest_framework import serializers

from apps.core.models import BASE_FIELDS
from apps.core.serializers import BaseModelSerializer

from .models import (
    Banque,
    Categorie,
    Echelon,
    Fonction,
    Grade,
    MotifSortie,
    Parametre,
    PieceRequise,
    Site,
    TypeContrat,
    TypeDocument,
    TypeSuspension,
    UniteOrganisationnelle,
)


class SiteSerializer(BaseModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "code", "nom", "ville", "siege", "date_fermeture", *BASE_FIELDS]


class SiteResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "code", "nom"]


class UniteOrganisationnelleSerializer(BaseModelSerializer):
    type_libelle = serializers.CharField(source="get_type_display", read_only=True)
    site = SiteResumeSerializer(read_only=True)

    class Meta:
        model = UniteOrganisationnelle
        fields = [
            "id",
            "code",
            "nom",
            "type",
            "type_libelle",
            "parent",
            "site",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class CategorieSerializer(BaseModelSerializer):
    class Meta:
        model = Categorie
        fields = ["id", "code", "nom", "rang", "date_ouverture", "date_fermeture", *BASE_FIELDS]


class GradeSerializer(BaseModelSerializer):
    class Meta:
        model = Grade
        fields = [
            "id",
            "categorie",
            "code",
            "nom",
            "rang",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class EchelonSerializer(BaseModelSerializer):
    libelle = serializers.CharField(read_only=True)

    class Meta:
        model = Echelon
        fields = [
            "id",
            "grade",
            "numero",
            "libelle",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class FonctionSerializer(BaseModelSerializer):
    """A job function with its nature and the nature's French label (fonctions D16)."""

    nature_libelle = serializers.CharField(source="get_nature_display", read_only=True)

    class Meta:
        model = Fonction
        fields = [
            "id",
            "code",
            "nom",
            "nature",
            "nature_libelle",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class TypeContratSerializer(BaseModelSerializer):
    """A contract type with the two rules phase 2.3 reads (contract types D17)."""

    class Meta:
        model = TypeContrat
        fields = [
            "id",
            "code",
            "nom",
            "duree_determinee",
            "periode_essai",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class TypeDocumentSerializer(BaseModelSerializer):
    class Meta:
        model = TypeDocument
        fields = ["id", "code", "nom", "date_ouverture", "date_fermeture", *BASE_FIELDS]


class PieceRequiseSerializer(BaseModelSerializer):
    """A document an event kind requires; the client joins it to its type by id
    (document types D19)."""

    evenement_libelle = serializers.CharField(source="get_evenement_display", read_only=True)

    class Meta:
        model = PieceRequise
        fields = [
            "id",
            "evenement",
            "evenement_libelle",
            "type_document",
            "obligatoire",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class DocumentRowSerializer(BaseModelSerializer):
    """A row that rests on a document type, named so the screen needs no second list
    (exit reasons D19)."""

    type_document_libelle = serializers.CharField(source="type_document", read_only=True)


class MotifSortieSerializer(DocumentRowSerializer):
    class Meta:
        model = MotifSortie
        fields = [
            "id",
            "code",
            "nom",
            "type_document",
            "type_document_libelle",
            "retraite",
            "deces",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class TypeSuspensionSerializer(DocumentRowSerializer):
    class Meta:
        model = TypeSuspension
        fields = [
            "id",
            "code",
            "nom",
            "type_document",
            "type_document_libelle",
            "compte_anciennete",
            "duree_max_mois",
            "renouvellements_max",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class BanqueSerializer(BaseModelSerializer):
    """A bank (banks D17); swift is "" when unknown."""

    class Meta:
        model = Banque
        fields = ["id", "code", "nom", "swift", "date_ouverture", "date_fermeture", *BASE_FIELDS]


class ParametreSerializer(BaseModelSerializer):
    """A dated value of a general parameter, with its label and unit (general parameters
    D17)."""

    cle_libelle = serializers.CharField(source="get_cle_display", read_only=True)
    unite = serializers.CharField(read_only=True)

    class Meta:
        model = Parametre
        fields = [
            "id",
            "cle",
            "cle_libelle",
            "unite",
            "valeur",
            "date_ouverture",
            "date_fermeture",
            *BASE_FIELDS,
        ]


class PeriodeSerializer(serializers.Serializer):
    """Query parameters of the lists: open on a date (default today), or all (D20, D21)."""

    date = serializers.DateField(required=False)
    toutes = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        attrs.setdefault("date", timezone.localdate())
        return attrs
