from django.contrib import admin

from apps.core.admin import BaseModelAdmin

from .models import Agent


@admin.register(Agent)
class AgentAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Agents in Django admin until the creation form of phase 2.9 (agent identity D16).

    The matricule is read-only once saved (D9); an agent is never deleted (D10),
    not even by a superuser.
    """

    list_display = ["matricule", "nom", "postnom", "prenom", "sexe", "date_naissance"]
    list_filter = ["sexe"]
    search_fields = ["matricule", "nom", "postnom", "prenom"]
    fields = [
        "matricule",
        "nom",
        "postnom",
        "prenom",
        "sexe",
        "date_naissance",
        "lieu_naissance",
        "nationalite",
    ]

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        return [*fields, "matricule"] if obj is not None else fields

    def has_delete_permission(self, request, obj=None):
        return False
