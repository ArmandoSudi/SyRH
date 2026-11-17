from rest_framework import viewsets

from apps.accounts.permissions import HasModuleAccess

from .models import Site, UniteOrganisationnelle
from .serializers import PeriodeSerializer, SiteSerializer, UniteOrganisationnelleSerializer


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
