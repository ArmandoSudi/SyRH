from rest_framework.routers import SimpleRouter

from .views import AgentViewSet

router = SimpleRouter()
router.register("", AgentViewSet, basename="agents-agent")

urlpatterns = router.urls
