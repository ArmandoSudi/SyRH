from django.conf import settings
from django.db import models

# The four fields every business model inherits, in the order they are shown.
BASE_FIELDS = ("date_creation", "date_modification", "cree_par", "modifie_par")


class BaseModel(models.Model):
    """Abstract base of every SyRH business model.

    Stamps each row with when it was created and last changed, and by whom.
    This is not the audit log (phase 0.6): only the latest modification is kept.

    The author is filled explicitly, never by middleware or signals:
    - API viewsets use core.mixins.AuthorMixin;
    - Django admin classes use core.admin.BaseModelAdmin;
    - scripts and imports set cree_par / modifie_par themselves, or leave them
      empty.

    QuerySet.update() and bulk_update() bypass save(): callers that use them
    set date_modification (and modifie_par) themselves.
    """

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

    class Meta:
        abstract = True

    def save(self, **kwargs):
        # A partial save still records when and by whom the row last changed.
        update_fields = kwargs.get("update_fields")
        if update_fields:
            kwargs["update_fields"] = {*update_fields, "date_modification", "modifie_par"}
        super().save(**kwargs)
