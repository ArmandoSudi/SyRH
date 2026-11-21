from django.db.models import Prefetch
from rest_framework import viewsets

from apps.accounts.permissions import HasModuleAccess

from .models import Agent, Contrat
from .serializers import AgentDetailSerializer, AgentSerializer


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    """Agents by name, read by every profile opening Agents (agent identity D13, D18).

    Read-only in this phase: the creation form of 2.9 adds writes, the list
    screen of 2.8 adds search and pagination. The detail adds the contact
    details (contact details D18), the hiring date and the contracts (contract D19),
    in two queries.
    """

    queryset = Agent.objects.all()
    permission_classes = [HasModuleAccess("agents")]
    pagination_class = None

    def get_serializer_class(self):
        return AgentDetailSerializer if self.action == "retrieve" else AgentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "retrieve":
            return queryset
        contrats = Contrat.objects.select_related("type_contrat").order_by("date_debut")
        return queryset.select_related("coordonnees").prefetch_related(
            Prefetch("contrats", queryset=contrats)
        )
