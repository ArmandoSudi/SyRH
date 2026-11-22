from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModuleAccess
from apps.core.mixins import request_author

from .engagement import EngagementPermission, EngagementSerializer, engager
from .models import Affectation, Agent, Classement, CompteBancaire, Contrat
from .recherche import AgentPagination, RechercheSerializer, rechercher
from .serializers import AgentDetailSerializer, AgentSerializer, ComptesBancairesSerializer


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    """Agents by name, read by every profile opening Agents (agent identity D13, D18).

    Read-only in this phase: the creation form of 2.9 adds writes, the list
    screen of 2.8 adds search and pagination. The detail adds the contact
    details (contact details D18), the hiring date and the contracts (contract D19)
    and both position histories (position history D19). The list and the detail
    show the assignment and classification in force today (D20), read from the
    prefetched histories: a fixed number of queries whatever the number of agents.

    The bank accounts are pay data: they have their own endpoint, read by the
    profiles opening Paie only, and never appear in the list or the detail
    (bank account D15, D18).
    """

    queryset = Agent.objects.all()
    permission_classes = [HasModuleAccess("agents"), EngagementPermission]
    pagination_class = AgentPagination

    def create(self, request, *args, **kwargs):
        """POST /api/agents/: hire an agent, all or nothing (agent creation form D1 to D5)."""
        data = EngagementSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        agent = engager(data.validated_data, request_author(request))
        detail = self.get_queryset_for_detail().get(pk=agent.pk)
        serializer = AgentDetailSerializer(detail, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset_for_detail(self):
        action, self.action = self.action, "retrieve"
        try:
            return self.get_queryset()
        finally:
            self.action = action

    def get_serializer_class(self):
        return AgentDetailSerializer if self.action == "retrieve" else AgentSerializer

    def recherche(self) -> dict:
        """The validated search parameters of the list (agent list D4, D10)."""
        if not hasattr(self, "_recherche"):
            params = RechercheSerializer(data=self.request.query_params)
            params.is_valid(raise_exception=True)
            self._recherche = params.validated_data
        return self._recherche

    def get_serializer_context(self):
        # The list reads positions and status on its ?date= (agent list D9).
        jour = self.recherche()["date"] if self.action == "list" else timezone.localdate()
        return {**super().get_serializer_context(), "aujourdhui": jour}

    def get_queryset(self):
        if self.action == "comptes_bancaires":
            comptes = CompteBancaire.objects.select_related("banque").order_by("date_effet")
            return Agent.objects.prefetch_related(Prefetch("comptes_bancaires", queryset=comptes))
        affectations = Affectation.objects.select_related("unite", "fonction").order_by(
            "date_effet"
        )
        classements = Classement.objects.select_related("echelon__grade__categorie").order_by(
            "date_effet"
        )
        base = rechercher(self.recherche()) if self.action == "list" else super().get_queryset()
        queryset = base.prefetch_related(
            Prefetch("affectations", queryset=affectations),
            Prefetch("classements", queryset=classements),
        )
        if self.action != "retrieve":
            return queryset
        contrats = Contrat.objects.select_related("type_contrat").order_by("date_debut")
        return queryset.select_related("coordonnees").prefetch_related(
            Prefetch("contrats", queryset=contrats)
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="comptes-bancaires",
        permission_classes=[HasModuleAccess("agents"), HasModuleAccess("paie")],
    )
    def comptes_bancaires(self, request, pk=None):
        """GET /api/agents/<id>/comptes-bancaires/ (bank account D18)."""
        serializer = ComptesBancairesSerializer(
            self.get_object(), context=self.get_serializer_context()
        )
        return Response(serializer.data)
