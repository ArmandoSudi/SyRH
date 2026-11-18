from django.utils import timezone
from rest_framework import serializers

from apps.core.models import BASE_FIELDS
from apps.core.serializers import BaseModelSerializer

from .models import Categorie, Echelon, Grade, Site, UniteOrganisationnelle


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


class PeriodeSerializer(serializers.Serializer):
    """Query parameters of the lists: open on a date (default today), or all (D20, D21)."""

    date = serializers.DateField(required=False)
    toutes = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        attrs.setdefault("date", timezone.localdate())
        return attrs
