from django.contrib.auth.models import AbstractUser
from django.db import models

from .roles import MODULES


class User(AbstractUser):
    """Utilisateur du SIRH.

    Custom model declared from the first migration so that fields (service,
    link to the agent record, ...) can be added later without a painful swap.
    """


class ModuleAccess(models.Model):
    """Carries one "access" permission per SyRH module; has no table.

    accounts.access_paie opens the Paie module, and so on (see roles.MODULES).
    """

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            (f"access_{key}", f"Accès au module {label}") for key, label in MODULES.items()
        ]
        verbose_name = "accès aux modules"

    def __str__(self):
        return self._meta.verbose_name
