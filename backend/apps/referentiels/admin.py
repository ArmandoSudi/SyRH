from django.contrib import admin
from django.utils import timezone

from apps.core.admin import BaseModelAdmin

from .models import (
    Categorie,
    Echelon,
    Fonction,
    Grade,
    Site,
    TypeContrat,
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
    """Catégories, grades and échelons. No inlines: BaseModelAdmin stamps the
    author on the main row only (classification D22)."""

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        parent = self.model.PARENT
        if obj is None or parent is None:
            return readonly
        # A reform closes the row and opens a new one (D11).
        return (parent, *readonly)


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
