from rest_framework.permissions import BasePermission

from .roles import module_permission


def HasModuleAccess(module: str) -> type[BasePermission]:  # noqa: N802 (reads like a class)
    """Permission class requiring access to one SyRH module.

    Usage: permission_classes = [HasModuleAccess("paie")]. Anonymous requests
    get 401 (through SessionAuthentication), signed-in users without the
    module's permission get 403. An unknown module fails at import time.
    """
    required = module_permission(module)

    class _HasModuleAccess(BasePermission):
        message = "Vous n'avez pas accès à ce module."

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and user.has_perm(required))

    _HasModuleAccess.__name__ = f"HasModuleAccess_{module}"
    return _HasModuleAccess
