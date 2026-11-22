"""The documents of an agent's file, through the API (document storage D14, D15, D18, D19).

GET    /api/agents/<agent>/documents/                 the documents the user may read
POST   /api/agents/<agent>/documents/                 upload one (multipart)
GET    /api/agents/<agent>/documents/<id>/fichier/    the file, inline or as an attachment
POST   /api/agents/<agent>/documents/<id>/retrait/    retire it, with a reason

Module access is checked before the agent is looked up, so a profile without
Agents learns nothing about which ids exist. A confidential document the user may
not read is absent from the list and answers 404 (D14).
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.http import content_disposition_header
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.accounts.roles import module_permission
from apps.core.mixins import request_author
from apps.core.storage import UNREADABLE, DocumentIndechiffrable
from apps.referentiels.edition import as_drf_errors

from .documents import create_document
from .models import Agent, Document
from .serializers import DocumentSerializer, DocumentUploadSerializer, RetraitSerializer

logger = logging.getLogger(__name__)


class DocumentPermission(BasePermission):
    """Reading needs Agents; uploading add_document, retiring change_document (D15).

    Other methods are let through so that they answer 405, not 403.
    """

    message = "Vous ne pouvez pas modifier les pièces de cet agent."
    NEEDS = {"create": "agents.add_document", "retrait": "agents.change_document"}

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if not user.has_perm(module_permission("agents")):
            self.message = "Vous n'avez pas accès à ce module."
            return False
        needed = self.NEEDS.get(getattr(view, "action", None))
        return needed is None or user.has_perm(needed)


class DocumentViewSet(viewsets.GenericViewSet):
    permission_classes = [DocumentPermission]
    serializer_class = DocumentSerializer
    pagination_class = None

    def agent(self) -> Agent:
        if not hasattr(self, "_agent"):
            self._agent = get_object_or_404(Agent, pk=self.kwargs["agent_pk"])
        return self._agent

    def get_queryset(self):
        return (
            Document.objects.filter(agent=self.agent())
            .lisibles_par(self.request.user)
            .select_related("type_document", "agent", "cree_par", "retire_par")
            .order_by("-date_creation", "-id")
        )

    def list(self, request, agent_pk=None):
        queryset = self.get_queryset()
        if request.query_params.get("retires") not in ("1", "true"):
            queryset = queryset.filter(retire=False)
        return Response(self.get_serializer(queryset, many=True).data)

    def create(self, request, agent_pk=None):
        agent = self.agent()
        upload = DocumentUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        data = upload.validated_data
        try:
            document = create_document(
                agent,
                data["type_document"],
                data["fichier"],
                date_document=data.get("date_document"),
                auteur=request_author(request),
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(as_drf_errors(error)) from error
        document = self.get_queryset().get(pk=document.pk)
        return Response(self.get_serializer(document).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def fichier(self, request, agent_pk=None, pk=None):
        """The decrypted file, with headers that stop the browser guessing or caching (D19)."""
        document = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            with document.fichier.open() as opened:
                content = opened.read()
        except DocumentIndechiffrable:
            logger.error(
                "Document %s cannot be decrypted (%s).", document.pk, document.fichier.name
            )
            return Response({"detail": UNREADABLE}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        attachment = request.query_params.get("telechargement") in ("1", "true")
        response = HttpResponse(content, content_type=document.type_mime)
        response["Content-Disposition"] = content_disposition_header(
            attachment, document.nom_original
        )
        response["Content-Length"] = str(len(content))
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response

    @action(detail=True, methods=["post"])
    def retrait(self, request, agent_pk=None, pk=None):
        document = get_object_or_404(self.get_queryset(), pk=pk)
        retrait = RetraitSerializer(data=request.data)
        retrait.is_valid(raise_exception=True)
        try:
            document.retirer(retrait.validated_data["motif"], auteur=request_author(request))
        except DjangoValidationError as error:
            raise serializers.ValidationError(as_drf_errors(error)) from error
        document = self.get_queryset().get(pk=document.pk)
        return Response(self.get_serializer(document).data)
