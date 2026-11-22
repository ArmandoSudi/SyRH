from rest_framework import viewsets

from apps.accounts.permissions import HasModuleAccess

from .edition import EditionMixin
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
from .serializers import (
    BanqueSerializer,
    CategorieSerializer,
    EchelonSerializer,
    FonctionSerializer,
    GradeSerializer,
    MotifSortieSerializer,
    ParametreSerializer,
    PeriodeSerializer,
    PieceRequiseSerializer,
    SiteSerializer,
    TypeContratSerializer,
    TypeDocumentSerializer,
    TypeSuspensionSerializer,
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


class SiteViewSet(EditionMixin, PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """ARPTC sites. Editors create, correct and close them; a site has no opening date,
    so it has no successor (tree reference screens D1)."""

    REMPLACABLE = False
    serializer_class = SiteSerializer
    queryset = Site.objects.all()

    def open_on(self, queryset, day):
        return queryset.ouverts(day)


class UniteOrganisationnelleViewSet(EditionMixin, PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """Organisation units as a flat list with parent ids; the client builds the tree (D20).
    Editors write them (tree reference screens D1)."""

    serializer_class = UniteOrganisationnelleSerializer
    queryset = UniteOrganisationnelle.objects.select_related("site")

    def open_on(self, queryset, day):
        return queryset.ouvertes(day)


class ClassificationViewSet(PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """Reference rows as flat lists with parent ids, in their model's order (classification
    D24, D25), open at a date."""

    permission_classes = [HasModuleAccess("referentiels")]

    def open_on(self, queryset, day):
        return queryset.ouvertes(day)


class CategorieViewSet(EditionMixin, ClassificationViewSet):
    serializer_class = CategorieSerializer
    queryset = Categorie.objects.all()


class GradeViewSet(EditionMixin, ClassificationViewSet):
    serializer_class = GradeSerializer
    queryset = Grade.objects.all()


class EchelonViewSet(EditionMixin, ClassificationViewSet):
    serializer_class = EchelonSerializer
    queryset = Echelon.objects.select_related("grade")  # the label shows the grade code


class FonctionViewSet(EditionMixin, PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """Job functions, responsabilité first then by name (fonctions D15 to D17).
    Editors create, correct and replace them (reference data screens D3)."""

    serializer_class = FonctionSerializer
    queryset = Fonction.objects.all()

    def open_on(self, queryset, day):
        return queryset.ouvertes(day)


class TypeContratViewSet(EditionMixin, PeriodeMixin, viewsets.ReadOnlyModelViewSet):
    """Contract types by name, with their rules (contract types D16 to D18).
    Editors create, correct and replace them (reference data screens D3)."""

    serializer_class = TypeContratSerializer
    queryset = TypeContrat.objects.all()

    def open_on(self, queryset, day):
        return queryset.ouvertes(day)


class TypeDocumentViewSet(EditionMixin, ClassificationViewSet):
    """Kinds of supporting document, by name (document types D18, D19)."""

    serializer_class = TypeDocumentSerializer
    queryset = TypeDocument.objects.prefetch_related("groupes_autorises")


class PieceRequiseViewSet(EditionMixin, ClassificationViewSet):
    """The documents each event kind requires, in event order (document types D18, D19).
    The ordering joins the type for its name; the type itself is returned as an id."""

    serializer_class = PieceRequiseSerializer
    queryset = PieceRequise.objects.all()


class MotifSortieViewSet(EditionMixin, ClassificationViewSet):
    """Exit reasons by name, with their document and flags (exit reasons D18, D19)."""

    serializer_class = MotifSortieSerializer
    queryset = MotifSortie.objects.select_related("type_document")


class TypeSuspensionViewSet(EditionMixin, ClassificationViewSet):
    """Suspension types by name, with their document and rules (exit reasons D18, D19)."""

    serializer_class = TypeSuspensionSerializer
    queryset = TypeSuspension.objects.select_related("type_document")


class BanqueViewSet(EditionMixin, ClassificationViewSet):
    """Banks by name (banks D16, D17), written by Rémunération and the administrator."""

    serializer_class = BanqueSerializer
    queryset = Banque.objects.all()


class ParametreViewSet(EditionMixin, ClassificationViewSet):
    """General parameters in key order (general parameters D16, D17)."""

    serializer_class = ParametreSerializer
    queryset = Parametre.objects.all()
