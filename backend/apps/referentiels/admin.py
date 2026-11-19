from django.contrib import admin
from django.utils import timezone

from apps.core.admin import BaseModelAdmin

from .models import (
    Banque,
    Categorie,
    Echelon,
    Fonction,
    Grade,
    MotifSortie,
    PieceRequise,
    Site,
    TypeContrat,
    TypeDocument,
    TypeSuspension,
    UniteOrganisationnelle,
)


class OuvertFilter(admin.SimpleListFilter):
    """Open today or closed, by the first-closed-day rule (D7)."""

    title = "statut"
    parameter_name = "statut"

    def lookups(self, request, model_admin):
        return [("ouvert", "Ouvert aujourd'hui"), ("ferme", "Fermé")]

    def queryset(self, request, queryset):
        if self.value() not in ("ouvert", "ferme"):
            return queryset
        today = timezone.localdate()
        if queryset.model is Site:
            opened = queryset.ouverts(today)
        else:
            opened = queryset.ouvertes(today)
        if self.value() == "ouvert":
            return opened
        return queryset.exclude(pk__in=opened.values("pk"))


@admin.register(Site)
class SiteAdmin(BaseModelAdmin, admin.ModelAdmin):
    list_display = ["code", "nom", "ville", "siege", "date_fermeture"]
    list_filter = ["siege", OuvertFilter]
    search_fields = ["code", "nom", "ville"]
    fields = ["code", "nom", "ville", "siege", "date_fermeture"]


@admin.register(UniteOrganisationnelle)
class UniteOrganisationnelleAdmin(BaseModelAdmin, admin.ModelAdmin):
    list_display = ["code", "nom", "type", "parent", "site", "date_ouverture", "date_fermeture"]
    list_filter = ["type", "site", OuvertFilter]
    search_fields = ["code", "nom"]
    autocomplete_fields = ["parent", "site"]
    list_select_related = ["parent", "site"]
    fields = ["type", "code", "nom", "parent", "site", "date_ouverture", "date_fermeture"]

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if obj is None:
            return readonly
        # A restructuring closes the unit and opens a new one (D8).
        return (*UniteOrganisationnelle.FIXED, *readonly)


class ClassificationAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Rows with ClassificationRules: the classification, document types and required
    documents. The parent and the FIXED fields are read-only once saved. No inlines:
    BaseModelAdmin stamps the author on the main row only (classification D22)."""

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        fixed = ((self.model.PARENT,) if self.model.PARENT else ()) + self.model.FIXED
        if obj is None or not fixed:
            return readonly
        # A reform closes the row and opens a new one (D11).
        return (*fixed, *readonly)


@admin.register(Categorie)
class CategorieAdmin(ClassificationAdmin):
    list_display = ["code", "nom", "rang", "date_ouverture", "date_fermeture"]
    list_filter = [OuvertFilter]
    search_fields = ["code", "nom"]
    fields = ["code", "nom", "rang", "date_ouverture", "date_fermeture"]


@admin.register(Grade)
class GradeAdmin(ClassificationAdmin):
    list_display = ["code", "nom", "categorie", "rang", "date_ouverture", "date_fermeture"]
    list_filter = ["categorie", OuvertFilter]
    search_fields = ["code", "nom"]
    autocomplete_fields = ["categorie"]
    list_select_related = ["categorie"]
    fields = ["categorie", "code", "nom", "rang", "date_ouverture", "date_fermeture"]


@admin.register(Echelon)
class EchelonAdmin(ClassificationAdmin):
    list_display = ["grade", "numero", "date_ouverture", "date_fermeture"]
    list_filter = [("grade__categorie", admin.RelatedOnlyFieldListFilter), OuvertFilter]
    search_fields = ["grade__code", "grade__nom"]
    autocomplete_fields = ["grade"]
    list_select_related = ["grade", "grade__categorie"]
    fields = ["grade", "numero", "date_ouverture", "date_fermeture"]


@admin.register(Fonction)
class FonctionAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Job functions (fonctions D13). A rename closes the row and opens a successor."""

    list_display = ["code", "nom", "nature", "date_ouverture", "date_fermeture"]
    list_filter = ["nature", OuvertFilter]
    search_fields = ["code", "nom"]
    fields = ["code", "nom", "nature", "date_ouverture", "date_fermeture"]


@admin.register(TypeContrat)
class TypeContratAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Contract types (contract types D14). Changing a rule closes the type and opens a
    successor, so old contracts keep the rules they were signed under."""

    list_display = [
        "code", "nom", "duree_determinee", "periode_essai", "date_ouverture", "date_fermeture"
    ]  # fmt: skip
    list_filter = ["duree_determinee", "periode_essai", OuvertFilter]
    search_fields = ["code", "nom"]
    fields = [
        "code",
        "nom",
        "duree_determinee",
        "periode_essai",
        "date_ouverture",
        "date_fermeture",
    ]


@admin.register(TypeDocument)
class TypeDocumentAdmin(ClassificationAdmin):
    """Kinds of supporting document (document types D16)."""

    list_display = ["code", "nom", "date_ouverture", "date_fermeture"]
    list_filter = [OuvertFilter]
    search_fields = ["code", "nom"]  # also used by the requirement's autocomplete
    fields = ["code", "nom", "date_ouverture", "date_fermeture"]


@admin.register(PieceRequise)
class PieceRequiseAdmin(ClassificationAdmin):
    """The documents each event kind requires (document types D16). The event and the
    type are read-only once saved: a new rule closes the row and opens another (D9)."""

    list_display = ["evenement", "type_document", "obligatoire", "date_ouverture",
                    "date_fermeture"]  # fmt: skip
    list_filter = ["evenement", "obligatoire", OuvertFilter]
    search_fields = ["type_document__code", "type_document__nom"]
    autocomplete_fields = ["type_document"]
    list_select_related = ["type_document"]
    fields = ["evenement", "type_document", "obligatoire", "date_ouverture", "date_fermeture"]


@admin.register(MotifSortie)
class MotifSortieAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Exit reasons (exit reasons D16). Changing a rule closes the reason and opens a
    successor, so an old exit keeps the reason it was recorded under (D8)."""

    list_display = ["code", "nom", "type_document", "retraite", "deces", "date_ouverture",
                    "date_fermeture"]  # fmt: skip
    list_filter = ["retraite", "deces", OuvertFilter]
    search_fields = ["code", "nom"]
    autocomplete_fields = ["type_document"]
    list_select_related = ["type_document"]
    fields = ["code", "nom", "type_document", "retraite", "deces", "date_ouverture",
              "date_fermeture"]  # fmt: skip


@admin.register(TypeSuspension)
class TypeSuspensionAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Suspension types (exit reasons D16)."""

    list_display = ["code", "nom", "type_document", "compte_anciennete", "duree_max_mois",
                    "renouvellements_max", "date_ouverture", "date_fermeture"]  # fmt: skip
    list_filter = ["compte_anciennete", OuvertFilter]
    search_fields = ["code", "nom"]
    autocomplete_fields = ["type_document"]
    list_select_related = ["type_document"]
    fields = ["code", "nom", "type_document", "compte_anciennete", "duree_max_mois",
              "renouvellements_max", "date_ouverture", "date_fermeture"]  # fmt: skip


@admin.register(Banque)
class BanqueAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Banks (banks D14), edited by Rémunération and the administrator. A renamed or
    merged bank is closed and a successor opened (D7)."""

    list_display = ["code", "nom", "swift", "date_ouverture", "date_fermeture"]
    list_filter = [OuvertFilter]
    search_fields = ["code", "nom", "swift"]
    fields = ["code", "nom", "swift", "date_ouverture", "date_fermeture"]
