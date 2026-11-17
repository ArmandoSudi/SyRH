from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

# Scope of account administration entries (users, groups, permissions): every
# reader of the audit log sees them, whatever modules they open.
COMPTES = "comptes"

IMMUTABLE = "Le journal d'audit ne peut pas être modifié."


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionError(IMMUTABLE)

    def delete(self):
        raise PermissionError(IMMUTABLE)


class EntreeAudit(models.Model):
    """One change to one row: who, when, what, old and new values (TRA-10).

    Append-only. The model refuses to save an existing entry or delete one, and
    a PostgreSQL trigger refuses UPDATE and DELETE on the table (migration 0001).
    """

    class Action(models.TextChoices):
        CREATION = "creation", "Création"
        MODIFICATION = "modification", "Modification"
        SUPPRESSION = "suppression", "Suppression"

    date = models.DateTimeField("date", default=timezone.now, editable=False)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    action = models.CharField("action", max_length=20, choices=Action.choices)
    table = models.ForeignKey(
        ContentType, verbose_name="table", on_delete=models.PROTECT, related_name="+"
    )
    objet_id = models.BigIntegerField("identifiant de la ligne")
    objet_libelle = models.CharField("libellé de la ligne", max_length=255)
    module = models.CharField("module", max_length=30)
    # [{"champ", "libelle", "avant", "apres"}] or, for a many-to-many field,
    # [{"champ", "libelle", "ajoutes", "retires"}]. See apps.audit.service.
    changements = models.JSONField("changements", default=list)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        verbose_name = "entrée du journal d'audit"
        verbose_name_plural = "entrées du journal d'audit"
        ordering = ["-date", "-id"]
        default_permissions = ()
        indexes = [
            models.Index(fields=["-date"], name="audit_date_idx"),
            models.Index(fields=["table", "objet_id"], name="audit_objet_idx"),
            models.Index(fields=["module", "-date"], name="audit_module_date_idx"),
        ]

    def __str__(self):
        return f"{self.get_action_display()} — {self.objet_libelle}"

    def save(self, **kwargs):
        if not self._state.adding:
            raise PermissionError(IMMUTABLE)
        super().save(**kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(IMMUTABLE)
