from django.db.models import Q
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from apps.accounts.permissions import HasModuleAccess
from apps.accounts.roles import MODULES, module_permission

from .models import COMPTES, EntreeAudit
from .serializers import EntreeAuditDetailSerializer, EntreeAuditSerializer, FiltresSerializer


def visible_scopes(user) -> list[str]:
    """Modules whose entries the reader may see, plus account administration (D21)."""
    return [m for m in MODULES if user.has_perm(module_permission(m))] + [COMPTES]


class AuditPagination(PageNumberPagination):
    page_size = 50


class EntreeAuditViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit log. Each reader sees only the entries of their modules.

    An entry outside them answers 404 on detail, as if it did not exist (D23).
    """

    permission_classes = [HasModuleAccess("audit")]
    pagination_class = AuditPagination

    def get_serializer_class(self):
        return EntreeAuditDetailSerializer if self.action == "retrieve" else EntreeAuditSerializer

    def get_queryset(self):
        return EntreeAudit.objects.filter(
            module__in=visible_scopes(self.request.user)
        ).select_related("auteur", "table")

    def filter_queryset(self, queryset):
        if self.action != "list":
            return queryset
        filtres = FiltresSerializer(data=self.request.query_params)
        filtres.is_valid(raise_exception=True)
        values = filtres.validated_data

        if "date_debut" in values:
            queryset = queryset.filter(date__date__gte=values["date_debut"])
        if "date_fin" in values:
            queryset = queryset.filter(date__date__lte=values["date_fin"])
        if "auteur" in values:
            text = values["auteur"]
            queryset = queryset.filter(
                Q(auteur__username__icontains=text)
                | Q(auteur__first_name__icontains=text)
                | Q(auteur__last_name__icontains=text)
            )
        for name in ("module", "action", "table"):
            if name in values:
                queryset = queryset.filter(**{name: values[name]})
        if "objet" in values:
            queryset = queryset.filter(objet_id=values["objet"])
        return queryset
