"""An agent's events and the documents attached to them (documents on events D19 to D22).

GET   /api/agents/<agent>/evenements/                                       events + status
POST  /api/agents/<agent>/evenements/<modele>/<id>/pieces/                  attach a document
POST  /api/agents/<agent>/evenements/<modele>/<id>/pieces/<lien>/retrait/   remove a link

Module access is checked before the agent is looked up. Confidential documents
count in the status but are listed only to their readers (D18).
"""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.accounts.roles import module_permission
from apps.core.mixins import request_author
from apps.referentiels.edition import as_drf_errors

from .models import MODELES_EVENEMENT, Agent, Document, PieceJointe
from .pieces import etats_pieces_de
from .serializers import JoindreSerializer, etat_json

PIECE_INTROUVABLE = "Cette pièce n'existe pas dans le dossier de l'agent."


class EvenementPermission(BasePermission):
    """Reading needs Agents; attaching add_piecejointe, removing change_piecejointe (D20).

    Other methods are let through so that they answer 405, not 403.
    """

    message = "Vous ne pouvez pas joindre de pièces aux événements de cet agent."
    NEEDS = {"joindre": "agents.add_piecejointe", "retrait": "agents.change_piecejointe"}

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if not user.has_perm(module_permission("agents")):
            self.message = "Vous n'avez pas accès à ce module."
            return False
        needed = self.NEEDS.get(getattr(view, "action", None))
        return needed is None or user.has_perm(needed)


class EvenementViewSet(viewsets.ViewSet):
    permission_classes = [EvenementPermission]

    def agent(self) -> Agent:
        return get_object_or_404(Agent, pk=self.kwargs["agent_pk"])

    def evenement(self, agent: Agent):
        """The event row named in the URL; 404 unless it is one of the agent's."""
        modele = self.kwargs["modele"]
        if modele not in MODELES_EVENEMENT:
            raise Http404
        content_type = ContentType.objects.get_by_natural_key("agents", modele)
        model = content_type.model_class()
        return content_type, get_object_or_404(model, pk=self.kwargs["objet_id"], agent=agent)

    def etat(self, agent: Agent, cle: str) -> dict:
        etats = etats_pieces_de(agent.pk, self.request.user)
        return etat_json(next(e for e in etats if e.evenement.cle == cle))

    def list(self, request, agent_pk=None):
        agent = self.agent()
        return Response([etat_json(e) for e in etats_pieces_de(agent.pk, request.user)])

    def joindre(self, request, agent_pk=None, modele=None, objet_id=None):
        agent = self.agent()
        content_type, objet = self.evenement(agent)
        data = JoindreSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        document = (
            Document.objects.filter(agent=agent, pk=data.validated_data["document"])
            .lisibles_par(request.user)
            .first()
        )
        if document is None:
            raise serializers.ValidationError({"document": [PIECE_INTROUVABLE]})
        author = request_author(request)
        lien = PieceJointe(
            document=document, content_type=content_type, objet_id=objet.pk,
            cree_par=author, modifie_par=author,
        )  # fmt: skip
        try:
            lien.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError(as_drf_errors(error)) from error
        return Response(self.etat(agent, f"{modele}-{objet.pk}"), status=status.HTTP_201_CREATED)

    def retrait(self, request, agent_pk=None, modele=None, objet_id=None, lien=None):
        agent = self.agent()
        content_type, objet = self.evenement(agent)
        lisibles = Document.objects.filter(agent=agent).lisibles_par(request.user).values("pk")
        row = get_object_or_404(
            PieceJointe, pk=lien, content_type=content_type, objet_id=objet.pk,
            document__in=lisibles,
        )  # fmt: skip
        try:
            row.retirer(auteur=request_author(request))
        except DjangoValidationError as error:
            raise serializers.ValidationError(as_drf_errors(error)) from error
        return Response(self.etat(agent, f"{modele}-{objet.pk}"))
