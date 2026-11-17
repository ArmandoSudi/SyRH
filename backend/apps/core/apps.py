from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Socle commun"

    def ready(self):
        from . import checks  # noqa: F401 (registers the system checks)
