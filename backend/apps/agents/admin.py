from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.core.mixins import request_author

from .models import (
    Affectation,
    Agent,
    Classement,
    CompteBancaire,
    Contrat,
    Coordonnees,
    Document,
)


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


@admin.register(CompteBancaire)
class CompteBancaireAdmin(BaseModelAdmin, admin.ModelAdmin):
    """Bank accounts on their own page, for Rémunération (bank account D17).

    Rémunération cannot change agents, so the accounts are not an inline of the
    agent page. The agent is picked by autocomplete and fixed once saved (D4);
    an account is never deleted (D14).
    """

    list_display = ["matricule", "agent", "banque", "numero", "date_effet"]
    list_filter = ["banque"]
    list_select_related = ["agent", "banque"]
    search_fields = ["agent__matricule", "agent__nom", "agent__postnom", "agent__prenom", "numero"]
    autocomplete_fields = ["agent"]
    fields = ["agent", "banque", "numero", "date_effet"]
    ordering = ["agent__matricule", "date_effet"]

    @admin.display(description="matricule", ordering="agent__matricule")
    def matricule(self, obj):
        return obj.agent.matricule

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        return ["agent", *fields] if obj is not None else fields

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Document)
class DocumentAdmin(BaseModelAdmin, admin.ModelAdmin):
    """The scanned documents, read-only (document storage D15).

    Uploads go through the API, where every check runs (format, size,
    duplicates); the admin only lists them. Confidential documents are hidden
    from those outside their type's groups (D14). Nothing is deleted (D17).
    """

    list_display = ["matricule", "agent", "type_document", "nom_original", "date_creation",
                    "retire"]  # fmt: skip
    list_filter = ["retire", "type_document"]
    list_select_related = ["agent", "type_document"]
    search_fields = [
        "agent__matricule", "agent__nom", "agent__postnom", "agent__prenom", "nom_original"
    ]  # fmt: skip
    fields = [
        "agent", "type_document", "nom_original", "type_mime", "taille", "date_document",
        "retire", "motif_retrait", "date_retrait", "retire_par",
    ]  # fmt: skip
    ordering = ["agent__matricule", "-date_creation"]

    @admin.display(description="matricule", ordering="agent__matricule")
    def matricule(self, obj):
        return obj.agent.matricule

    def get_queryset(self, request):
        return super().get_queryset(request).lisibles_par(request.user)

    def get_readonly_fields(self, request, obj=None):
        return [*self.fields, *super().get_readonly_fields(request, obj)]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
