"""Write audit entries. Every capture path goes through record().

Callers take a snapshot before the change and one after, then call record()
with the changes between them, in the same transaction as the change (D10).
"""

from django.contrib.contenttypes.models import ContentType

from apps.core.models import BASE_FIELDS

from .models import EntreeAudit
from .values import MASK, MASKED_FIELDS, label, render

Action = EntreeAudit.Action

# Not logged as changes: the entry holds the date and author, and last_login
# moves on every sign-in (D6).
SKIPPED_FIELDS = frozenset({*BASE_FIELDS, "last_login"})


def _logged_fields(model, only=None):
    for field in model._meta.concrete_fields:
        if field.primary_key or field.name in SKIPPED_FIELDS:
            continue
        if only is not None and field.name not in only and field.attname not in only:
            continue
        yield field


def snapshot(instance, only=None) -> dict:
    """Raw values of the logged fields, keyed by field name."""
    return {
        f.name: getattr(instance, f.attname) for f in _logged_fields(instance._meta.model, only)
    }


def m2m_snapshot(instance, names) -> dict[str, set]:
    """Primary keys of the related rows of each many-to-many field."""
    if instance.pk is None:
        return {name: set() for name in names}
    return {name: set(getattr(instance, name).values_list("pk", flat=True)) for name in names}


def _empty(value) -> bool:
    return value is None or value == ""


def changes(model, before: dict, after: dict) -> list[dict]:
    """Changed fields between two snapshots, in field order, with French labels.

    A creation passes before={}, a deletion after={}: empty values are left out.
    """
    result = []
    for field in _logged_fields(model):
        old, new = before.get(field.name), after.get(field.name)
        if old == new or (_empty(old) and _empty(new)):
            continue
        entry = {"champ": field.name, "libelle": str(field.verbose_name)}
        if field.name in MASKED_FIELDS:
            entry |= {
                "avant": None if _empty(old) else MASK,
                "apres": None if _empty(new) else MASK,
            }
        else:
            avant, apres = render(field, old), render(field, new)
            if avant == apres:  # same value once rendered (a datetime's microseconds)
                continue
            entry |= {"avant": avant, "apres": apres}
        result.append(entry)
    return result


def m2m_changes(model, before: dict[str, set], after: dict[str, set]) -> list[dict]:
    """Rows added to and removed from each many-to-many field, as labels."""
    result = []
    for name in after.keys() | before.keys():
        added = after.get(name, set()) - before.get(name, set())
        removed = before.get(name, set()) - after.get(name, set())
        if not added and not removed:
            continue
        field = model._meta.get_field(name)
        rows = {
            obj.pk: label(obj) for obj in field.related_model.objects.filter(pk__in=added | removed)
        }
        result.append(
            {
                "champ": name,
                "libelle": str(field.verbose_name),
                "ajoutes": sorted(rows.get(pk, str(pk)) for pk in added),
                "retires": sorted(rows.get(pk, str(pk)) for pk in removed),
            }
        )
    return sorted(result, key=lambda change: change["champ"])


def _author_id(auteur):
    if auteur is None:
        return None
    if isinstance(auteur, int):
        return auteur
    return auteur.pk if getattr(auteur, "is_authenticated", False) else None


def record(
    instance,
    action,
    changements,
    *,
    module,
    auteur=None,
    objet_id=None,
    libelle=None,
):
    """Write one entry; a modification without change writes nothing (D8).

    auteur is a user, a user id or None (system write). objet_id and libelle
    default to the instance's; pass them for a row that was just deleted.
    """
    if action == Action.MODIFICATION and not changements:
        return None
    return EntreeAudit.objects.create(
        auteur_id=_author_id(auteur),
        action=action,
        table=ContentType.objects.get_for_model(instance, for_concrete_model=True),
        objet_id=instance.pk if objet_id is None else objet_id,
        objet_libelle=(str(instance) if libelle is None else libelle)[:255],
        module=module,
        changements=changements,
    )
