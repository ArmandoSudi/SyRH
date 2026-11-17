from rest_framework.routers import SimpleRouter

from .views import SiteViewSet, UniteOrganisationnelleViewSet

router = SimpleRouter()
router.register("sites", SiteViewSet, basename="referentiels-site")
router.register("unites", UniteOrganisationnelleViewSet, basename="referentiels-unite")

urlpatterns = router.urls
