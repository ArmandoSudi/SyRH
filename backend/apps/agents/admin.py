from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.core.mixins import request_author

from .models import Affectation, Agent, Classement, Contrat, Coordonnees


class CoordonneesInline(admin.StackedInline):
    """An agent's contact details, on the agent page (contact details D16).

    One row at most, never deleted (D13). Its author is stamped by
    AgentAdmin.save_formset, so the audit log names the editor.
    """

    model = Coordonnees
    max_num = 1
    can_delete = False
    fieldsets = [
        ("Adresse", {"fields": ["adresse", "commune", "ville"]}),
        ("Téléphones et courriel", {"fields": ["telephone", "telephone_secondaire", "courriel"]}),
        (
            "Personne à contacter en cas d'urgence",
            {"fields": ["urgence_nom", "urgence_lien", "urgence_telephone"]},
        ),
    ]


class ContratInline(admin.TabularInline):
    """An agent's successive contracts, in date order, on the agent page (contract D17).

    Never deleted (D14); one empty row to add the next contract. Authors are
    stamped by AgentAdmin.save_formset.
    """

    model = Contrat
    extra = 1
    can_delete = False
    fields = ["type_contrat", "date_debut", "date_fin", "fin_periode_essai"]
    ordering = ["date_debut"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("type_contrat", "agent")


class AffectationInline(admin.TabularInline):
    """An agent's assignments, in date order, on the agent page (position history D18).

    Never deleted (D15); one empty row to add the next one. Authors are stamped
    by AgentAdmin.save_formset.
    """

    model = Affectation
    extra = 1
    can_delete = False
    fields = ["date_effet", "unite", "fonction"]
    ordering = ["date_effet"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("unite", "fonction", "agent")


class ClassementInline(admin.TabularInline):
    """An agent's classifications, in date order, on the agent page (position history
    D18). The échelon names its grade; never deleted (D15)."""

    model = Classement
    extra = 1
    can_delete = False
    fields = ["date_effet", "echelon"]
    ordering = ["date_effet"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("echelon__grade", "agent")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "echelon":
            kwargs["queryset"] = db_field.remote_field.model.objects.select_related("grade")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Agent)
class AgentAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Agents in Django admin until the creation form of phase 2.9 (agent identity D16).

    The matricule is read-only once saved (D9); an agent is never deleted (D10),
    not even by a superuser. Contact details, contracts, assignments and
    classifications are edited inline (contact details D16, contract D17,
    position history D18).
    """

    inlines = [CoordonneesInline, ContratInline, AffectationInline, ClassementInline]
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

    def save_formset(self, request, form, formset, change):
        author = request_author(request)
        for row in formset.save(commit=False):
            if row.pk is None:
                row.cree_par = author
            row.modifie_par = author
            row.save()
        formset.save_m2m()
