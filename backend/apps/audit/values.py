"""Turn field values into JSON that stays readable for years (D5)."""

import datetime
import uuid
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.utils import timezone

MASK = "••••••"

# Never stored, even hashed (D7).
MASKED_FIELDS = frozenset({"password"})


def label(obj) -> str:
    """Text label of a related row. Permissions show their name alone."""
    if isinstance(obj, Permission):
        return obj.name
    return str(obj)


def render(field, raw):
    """JSON form of a raw value (attname value, so a foreign key's id)."""
    if raw is None:
        return None
    if field.name in MASKED_FIELDS:
        return MASK
    if field.many_to_one or field.one_to_one:
        target = field.related_model._base_manager.filter(pk=raw).first()
        return {"id": raw, "libelle": label(target) if target is not None else str(raw)}
    if isinstance(raw, datetime.datetime):
        # Local time, to the second: the same instant always renders the same,
        # and a form that drops microseconds does not look like a change.
        if timezone.is_aware(raw):
            raw = timezone.localtime(raw)
        return raw.isoformat(timespec="seconds")
    if isinstance(raw, datetime.time):
        return raw.isoformat(timespec="seconds")
    if isinstance(raw, datetime.date):
        return raw.isoformat()
    if isinstance(raw, Decimal | uuid.UUID):
        return str(raw)
    if isinstance(raw, str | int | float | bool):
        return raw
    return str(raw)
