from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Utilisateur du SIRH.

    Custom model declared from the first migration so that fields (service,
    link to the agent record, ...) can be added later without a painful swap.
    """
