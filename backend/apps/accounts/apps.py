from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_groups(sender, **kwargs):
    from .roles import sync_groups

    sync_groups()


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "Comptes utilisateurs"

    def ready(self):
        # After migrate, once Django has created this app's permissions, make
        # sure every profile group exists in every environment.
        post_migrate.connect(_sync_groups, sender=self, dispatch_uid="accounts_sync_groups")
