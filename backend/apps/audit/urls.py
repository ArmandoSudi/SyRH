from rest_framework.routers import SimpleRouter

from .views import EntreeAuditViewSet

router = SimpleRouter()
router.register("entrees", EntreeAuditViewSet, basename="audit-entree")

urlpatterns = router.urls
