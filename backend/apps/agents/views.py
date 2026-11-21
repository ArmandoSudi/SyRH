from rest_framework import viewsets

from apps.accounts.permissions import HasModuleAccess

from .models import Agent
from .serializers import AgentSerializer


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    """Agents by name, read by every profile opening Agents (agent identity D13, D18).

    Read-only in this phase: the creation form of 2.9 adds writes, the list
    screen of 2.8 adds search and pagination.
    """

    serializer_class = AgentSerializer
    queryset = Agent.objects.all()
    permission_classes = [HasModuleAccess("agents")]
    pagination_class = None
