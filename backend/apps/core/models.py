from django.conf import settings
from django.db import models, transaction

# The four fields every business model inherits, in the order they are shown.
BASE_FIELDS = ("date_creation", "date_modification", "cree_par", "modifie_par")

UNAUDITED = (
    "QuerySet.{} would bypass the audit log on {}: use update_audited(auteur, ...) "
    "or save / delete each row."
)


class UnauditedWriteError(RuntimeError):
    """A bulk write that would leave no trace in the audit log."""


class BaseQuerySet(models.QuerySet):
    """Refuses bulk writes that skip save() and delete(), so the audit log has no gap.

    bulk_create() and bulk_update() are not blocked: their callers (data
    imports) record their entries themselves with apps.audit.service.record().
    """

    def update(self, **kwargs):
        raise UnauditedWriteError(UNAUDITED.format("update()", self.model.__name__))

    def delete(self):
        raise UnauditedWriteError(UNAUDITED.format("delete()", self.model.__name__))

    def update_audited(self, auteur, **values) -> int:
        """Set values on every row, one save (and one audit entry) per row."""
        count = 0
        with transaction.atomic():
            for obj in self.select_for_update():
                for name, value in values.items():
                    setattr(obj, name, value)
                obj.modifie_par = auteur
                obj.save()
                count += 1
        return count


class BaseModel(models.Model):
    """Abstract base of every SyRH business model.

    Stamps each row with when it was created and last changed, and by whom, and
    writes an audit entry for every creation, modification and deletion, in the
    same transaction (apps.audit).

    The author is filled explicitly, never by middleware or signals:
    - API viewsets use core.mixins.AuthorMixin;
    - Django admin classes use core.admin.BaseModelAdmin;
    - scripts and imports set cree_par / modifie_par themselves, or leave them
      empty, and pass auteur= to delete().

    Every concrete subclass declares the SyRH module it belongs to, a key of
    accounts.roles.MODULES; readers of the audit log see its entries only if
    they open that module. A system check enforces it (core.E001).

    QuerySet.update() and delete() raise UnauditedWriteError: use
    update_audited() or save / delete row by row. bulk_create() and
    bulk_update() bypass save(): their callers record audit entries themselves.
    """

    module: str = ""

    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_modification = models.DateTimeField("date de modification", auto_now=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="créé par",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
    )
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="modifié par",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
    )

    objects = BaseQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, **kwargs):
        from apps.audit import service

        # A partial save still records when and by whom the row last changed.
        update_fields = kwargs.get("update_fields")
        if update_fields:
            kwargs["update_fields"] = {*update_fields, "date_modification", "modifie_par"}

        with transaction.atomic():
            # Old values come from the database, not from this object (D12).
            old = None
            if not self._state.adding and self.pk is not None:
                old = type(self)._base_manager.filter(pk=self.pk).first()
            super().save(**kwargs)

            if old is None:
                service.record(
                    self,
                    service.Action.CREATION,
                    service.changes(type(self), {}, service.snapshot(self)),
                    module=self.module,
                    auteur=self.cree_par_id,
                )
            else:
                only = kwargs.get("update_fields")
                service.record(
                    self,
                    service.Action.MODIFICATION,
                    service.changes(
                        type(self), service.snapshot(old, only), service.snapshot(self, only)
                    ),
                    module=self.module,
                    auteur=self.modifie_par_id,
                )

    def delete(self, using=None, keep_parents=False, *, auteur=None):
        from apps.audit import service

        with transaction.atomic():
            objet_id, libelle = self.pk, str(self)
            before = service.snapshot(self)
            result = super().delete(using=using, keep_parents=keep_parents)
            service.record(
                self,
                service.Action.SUPPRESSION,
                service.changes(type(self), before, {}),
                module=self.module,
                auteur=auteur,
                objet_id=objet_id,
                libelle=libelle,
            )
        return result
