from django.contrib import admin
from django.utils import timezone

from apps.core.admin import BaseModelAdmin

from .models import Site, UniteOrganisationnelle


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
        if queryset.model is UniteOrganisationnelle:
            opened = queryset.ouvertes(today)
        else:
            opened = queryset.ouverts(today)
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
