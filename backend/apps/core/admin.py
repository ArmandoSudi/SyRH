from .mixins import request_author
from .models import BASE_FIELDS


class BaseModelAdmin:
    """ModelAdmin mixin for BaseModel subclasses.

    Usage: class SiteAdmin(BaseModelAdmin, admin.ModelAdmin). Records the
    admin user as author, of the row and of its audit entry, deletion included,
    and shows the dates and authors read-only, after any read-only fields the
    subclass declares.
    """

    def get_readonly_fields(self, request, obj=None):
        own = tuple(super().get_readonly_fields(request, obj))
        return own + tuple(name for name in BASE_FIELDS if name not in own)

    def save_model(self, request, obj, form, change):
        author = request_author(request)
        if not change:
            obj.cree_par = author
        obj.modifie_par = author
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        obj.delete(auteur=request_author(request))

    def delete_queryset(self, request, queryset):
        # QuerySet.delete() is refused on BaseModel: one audited delete per row.
        for obj in queryset:
            obj.delete(auteur=request_author(request))
