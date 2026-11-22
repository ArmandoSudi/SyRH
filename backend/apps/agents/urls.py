from django.urls import path
from rest_framework.routers import SimpleRouter

from .document_views import DocumentViewSet
from .views import AgentViewSet

router = SimpleRouter()
router.register("", AgentViewSet, basename="agents-agent")

documents = DocumentViewSet.as_view({"get": "list", "post": "create"})
fichier = DocumentViewSet.as_view({"get": "fichier"})
retrait = DocumentViewSet.as_view({"post": "retrait"})

urlpatterns = [
    path("<int:agent_pk>/documents/", documents, name="agents-documents"),
    path("<int:agent_pk>/documents/<int:pk>/fichier/", fichier, name="agents-document-fichier"),
    path("<int:agent_pk>/documents/<int:pk>/retrait/", retrait, name="agents-document-retrait"),
    *router.urls,
]
