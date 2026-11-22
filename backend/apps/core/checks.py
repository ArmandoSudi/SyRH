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


def document_key_errors(keys) -> list[checks.Error]:
    """core.E002: at least one valid Fernet key encrypts the documents (document storage D8)."""
    from cryptography.fernet import Fernet

    hint = (
        "Set SYRH_DOCUMENT_KEYS in backend/.env; generate a key with "
        '`uv run python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"`.'
    )
    if not keys:
        return [
            checks.Error("SYRH_DOCUMENT_KEYS is empty: documents cannot be encrypted.",
                         hint=hint, id="core.E002")
        ]  # fmt: skip
    errors = []
    for position, key in enumerate(keys, start=1):
        try:
            Fernet(key.strip().encode())
        except ValueError:
            errors.append(
                checks.Error(
                    f"Key number {position} of SYRH_DOCUMENT_KEYS is not a valid Fernet key.",
                    hint=hint,
                    id="core.E002",
                )
            )
    return errors


@checks.register()
def check_document_keys(app_configs=None, **kwargs):
    from django.conf import settings

    return document_key_errors(settings.SYRH_DOCUMENT_KEYS)
