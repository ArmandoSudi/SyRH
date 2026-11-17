from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.db import transaction

from apps.audit import service
from apps.audit.models import COMPTES

from .models import User


class AccountAuditMixin:
    """Writes one audit entry per account change made in Django admin.

    Captures the fields and the many-to-many sets (group membership,
    permissions), with the admin user as author and the scope "comptes".
    The snapshot taken before saving travels on the object itself: a ModelAdmin
    is shared by every request.
    """

    audit_m2m: tuple[str, ...] = ()

    def save_model(self, request, obj, form, change):
        before = ({}, {})  # a creation: everything is new
        if change:
            old = type(obj)._base_manager.get(pk=obj.pk)
            before = (service.snapshot(old), service.m2m_snapshot(old, self.audit_m2m))
        obj._audit_before = before
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        fields_before, m2m_before = getattr(obj, "_audit_before", ({}, {}))
        model = type(obj)
        changes = service.changes(model, fields_before, service.snapshot(obj))
        changes += service.m2m_changes(model, m2m_before, service.m2m_snapshot(obj, self.audit_m2m))
        service.record(
            obj,
            service.Action.MODIFICATION if change else service.Action.CREATION,
            changes,
            module=COMPTES,
            auteur=request.user,
        )


@admin.register(User)
class AuditedUserAdmin(AccountAuditMixin, UserAdmin):
    audit_m2m = ("groups", "user_permissions")

    def user_change_password(self, request, id, form_url=""):
        # Django's password form saves outside save_model: log it here, masked.
        with transaction.atomic():
            user = self.get_object(request, unquote(id))
            before = service.snapshot(user, ["password"]) if user else None
            response = super().user_change_password(request, id, form_url)
            if user is not None and request.method == "POST":
                user.refresh_from_db(fields=["password"])
                service.record(
                    user,
                    service.Action.MODIFICATION,
                    service.changes(User, before, service.snapshot(user, ["password"])),
                    module=COMPTES,
                    auteur=request.user,
                )
        return response


admin.site.unregister(Group)


@admin.register(Group)
class AuditedGroupAdmin(AccountAuditMixin, GroupAdmin):
    audit_m2m = ("permissions",)
