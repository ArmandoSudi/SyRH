from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_groups(sender, **kwargs):
    from django.apps import apps

    from .roles import sync_groups

    # post_migrate is sent once per app, in INSTALLED_APPS order, and each
    # app's permissions are created on its own signal. Wait for the last one,
    # so the permissions of every app (referentiels included) exist.
    last = [config for config in apps.get_app_configs() if config.models_module is not None][-1]
    if sender is last:
        sync_groups()


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "Comptes utilisateurs"

    def ready(self):
        # After migrate, once Django has created every app's permissions, make
        # sure every profile group exists in every environment.
        post_migrate.connect(_sync_groups, dispatch_uid="accounts_sync_groups")
