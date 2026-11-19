from rest_framework.routers import SimpleRouter

from .views import (
    CategorieViewSet,
    EchelonViewSet,
    FonctionViewSet,
    GradeViewSet,
    PieceRequiseViewSet,
    SiteViewSet,
    TypeContratViewSet,
    TypeDocumentViewSet,
    UniteOrganisationnelleViewSet,
)

router = SimpleRouter()
router.register("sites", SiteViewSet, basename="referentiels-site")
router.register("unites", UniteOrganisationnelleViewSet, basename="referentiels-unite")
router.register("categories", CategorieViewSet, basename="referentiels-categorie")
router.register("grades", GradeViewSet, basename="referentiels-grade")
router.register("echelons", EchelonViewSet, basename="referentiels-echelon")
router.register("fonctions", FonctionViewSet, basename="referentiels-fonction")
router.register("types-contrat", TypeContratViewSet, basename="referentiels-typecontrat")
router.register("types-document", TypeDocumentViewSet, basename="referentiels-typedocument")
router.register("pieces-requises", PieceRequiseViewSet, basename="referentiels-piecerequise")

urlpatterns = router.urls
