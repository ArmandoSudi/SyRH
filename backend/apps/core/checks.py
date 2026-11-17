from django.apps import apps
from django.core import checks


def module_errors(models) -> list[checks.Error]:
    """core.E001: each concrete BaseModel subclass names a known SyRH module."""
    from apps.accounts.roles import MODULES

    from .models import BaseModel

    errors = []
    for model in models:
        if not issubclass(model, BaseModel) or model._meta.abstract:
            continue
        if model.module not in MODULES:
            errors.append(
                checks.Error(
                    f"{model._meta.label} must declare its module, one of: {', '.join(MODULES)}.",
                    hint='Add a class attribute, for example module = "referentiels".',
                    obj=model,
                    id="core.E001",
                )
            )
    return errors


@checks.register(checks.Tags.models)
def check_base_model_modules(app_configs=None, **kwargs):
    return module_errors(apps.get_models())
