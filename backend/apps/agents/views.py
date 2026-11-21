from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import viewsets

from apps.accounts.permissions import HasModuleAccess

from .models import Affectation, Agent, Classement, Contrat
from .serializers import AgentDetailSerializer, AgentSerializer


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    """Agents by name, read by every profile opening Agents (agent identity D13, D18).

    Read-only in this phase: the creation form of 2.9 adds writes, the list
    screen of 2.8 adds search and pagination. The detail adds the contact
    details (contact details D18), the hiring date and the contracts (contract D19)
    and both position histories (position history D19). The list and the detail
    show the assignment and classification in force today (D20), read from the
    prefetched histories: a fixed number of queries whatever the number of agents.
    """

    queryset = Agent.objects.all()
    permission_classes = [HasModuleAccess("agents")]
    pagination_class = None

    def get_serializer_class(self):
        return AgentDetailSerializer if self.action == "retrieve" else AgentSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "aujourdhui": timezone.localdate()}

    def get_queryset(self):
        affectations = Affectation.objects.select_related("unite", "fonction").order_by(
            "date_effet"
        )
        classements = Classement.objects.select_related("echelon__grade__categorie").order_by(
            "date_effet"
        )
        queryset = (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch("affectations", queryset=affectations),
                Prefetch("classements", queryset=classements),
            )
        )
        if self.action != "retrieve":
            return queryset
        contrats = Contrat.objects.select_related("type_contrat").order_by("date_debut")
        return queryset.select_related("coordonnees").prefetch_related(
            Prefetch("contrats", queryset=contrats)
        )
