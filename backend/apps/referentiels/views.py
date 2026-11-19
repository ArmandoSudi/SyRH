from rest_framework import viewsets

from apps.accounts.permissions import HasModuleAccess

from .models import (
    Categorie,
    Echelon,
    Fonction,
    Grade,
    PieceRequise,
    Site,
    TypeContrat,
    TypeDocument,
    UniteOrganisationnelle,
)
from .serializers import (
    CategorieSerializer,
    EchelonSerializer,
    FonctionSerializer,
    GradeSerializer,
    PeriodeSerializer,
    PieceRequiseSerializer,
    SiteSerializer,
    TypeContratSerializer,
    TypeDocumentSerializer,
    UniteOrganisationnelleSerializer,
)


class PeriodeMixin:
    """The list returns the rows open on ?date= (default today), or all with ?toutes=1."""

    def filter_queryset(self, queryset):
        if self.action != "list":
            return queryset
        periode = PeriodeSerializer(data=self.request.query_params)
        periode.is_valid(raise_exception=True)
        if periode.validated_data["toutes"]:
            return queryset
        return self.open_on(queryset, periode.validated_data["date"])


class SiteViewSet(PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """ARPTC sites, read-only: they are edited in Django admin until phase 1.9."""

    permission_classes = [HasModuleAccess("referentiels")]
    serializer_class = SiteSerializer
    queryset = Site.objects.all()

    def open_on(self, queryset, day):
        return queryset.ouverts(day)


class UniteOrganisationnelleViewSet(PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """Organisation units as a flat list with parent ids; the client builds the tree (D20)."""

    permission_classes = [HasModuleAccess("referentiels")]
    serializer_class = UniteOrganisationnelleSerializer
    queryset = UniteOrganisationnelle.objects.select_related("site")

    def open_on(self, queryset, day):
        return queryset.ouvertes(day)


class ClassificationViewSet(PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """Classification rows as flat lists with parent ids, in grid order (classification
    D24, D25). Read-only: they are edited in Django admin until phase 1.9."""

    permission_classes = [HasModuleAccess("referentiels")]

    def open_on(self, queryset, day):
        return queryset.ouvertes(day)


class CategorieViewSet(ClassificationViewSet):
    serializer_class = CategorieSerializer
    queryset = Categorie.objects.all()


class GradeViewSet(ClassificationViewSet):
    serializer_class = GradeSerializer
    queryset = Grade.objects.all()


class EchelonViewSet(ClassificationViewSet):
    serializer_class = EchelonSerializer
    queryset = Echelon.objects.select_related("grade")  # the label shows the grade code


class FonctionViewSet(PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """Job functions, responsabilité first then by name (fonctions D15 to D17).
    Read-only: they are edited in Django admin until phase 1.9."""

    permission_classes = [HasModuleAccess("referentiels")]
    serializer_class = FonctionSerializer
    queryset = Fonction.objects.all()

    def open_on(self, queryset, day):
        return queryset.ouvertes(day)


class TypeContratViewSet(PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """Contract types by name, with their rules (contract types D16 to D18).
    Read-only: they are edited in Django admin until phase 1.9."""

    permission_classes = [HasModuleAccess("referentiels")]
    serializer_class = TypeContratSerializer
    queryset = TypeContrat.objects.all()

    def open_on(self, queryset, day):
        return queryset.ouvertes(day)


class TypeDocumentViewSet(ClassificationViewSet):
    """Kinds of supporting document, by name (document types D18, D19)."""

    serializer_class = TypeDocumentSerializer
    queryset = TypeDocument.objects.all()


class PieceRequiseViewSet(ClassificationViewSet):
    """The documents each event kind requires, in event order (document types D18, D19).
    The ordering joins the type for its name; the type itself is returned as an id."""

    serializer_class = PieceRequiseSerializer
    queryset = PieceRequise.objects.all()
