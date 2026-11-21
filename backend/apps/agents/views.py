from rest_framework import viewsets

from apps.accounts.permissions import HasModuleAccess

from .models import Agent
from .serializers import AgentDetailSerializer, AgentSerializer


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    """Agents by name, read by every profile opening Agents (agent identity D13, D18).

    Read-only in this phase: the creation form of 2.9 adds writes, the list
    screen of 2.8 adds search and pagination. The detail adds the contact
    details (contact details D18).
    """

    queryset = Agent.objects.all()
    permission_classes = [HasModuleAccess("agents")]
    pagination_class = None

    def get_serializer_class(self):
        return AgentDetailSerializer if self.action == "retrieve" else AgentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related("coordonnees") if self.action == "retrieve" else queryset
