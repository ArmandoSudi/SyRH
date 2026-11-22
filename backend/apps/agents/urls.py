from django.urls import path
from rest_framework.routers import SimpleRouter

from .document_views import DocumentViewSet
from .evenement_views import EvenementViewSet
from .views import AgentViewSet

router = SimpleRouter()
router.register("", AgentViewSet, basename="agents-agent")

documents = DocumentViewSet.as_view({"get": "list", "post": "create"})
fichier = DocumentViewSet.as_view({"get": "fichier"})
retrait = DocumentViewSet.as_view({"post": "retrait"})
evenements = EvenementViewSet.as_view({"get": "list"})
joindre = EvenementViewSet.as_view({"post": "joindre"})
detacher = EvenementViewSet.as_view({"post": "retrait"})
EVENEMENT = "<int:agent_pk>/evenements/<str:modele>/<int:objet_id>/pieces/"

urlpatterns = [
    path("<int:agent_pk>/documents/", documents, name="agents-documents"),
    path("<int:agent_pk>/documents/<int:pk>/fichier/", fichier, name="agents-document-fichier"),
    path("<int:agent_pk>/documents/<int:pk>/retrait/", retrait, name="agents-document-retrait"),
    path("<int:agent_pk>/evenements/", evenements, name="agents-evenements"),
    path(EVENEMENT, joindre, name="agents-evenement-joindre"),
    path(f"{EVENEMENT}<int:lien>/retrait/", detacher, name="agents-evenement-retrait"),
    *router.urls,
]
