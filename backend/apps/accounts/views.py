from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.audit import service
from apps.audit.models import COMPTES

from .authentication import SessionAuthentication
from .serializers import LoginSerializer, PasswordChangeSerializer, UserSerializer

# One message for every failure, so the API never reveals which accounts exist.
LOGIN_ERROR = "Identifiant ou mot de passe incorrect."


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    """Set the CSRF cookie the SPA needs before its first unsafe request."""
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    # DRF only checks CSRF for requests that already carry a session, so an
    # anonymous login would otherwise be open to login CSRF.
    SessionAuthentication().enforce_csrf(request)

    serializer = LoginSerializer(data=request.data)
    user = None
    if serializer.is_valid():
        # Unknown username, wrong password and inactive account all give None.
        user = authenticate(request, **serializer.validated_data)
    if user is None:
        raise ValidationError({"non_field_errors": [LOGIN_ERROR]})

    auth_login(request, user)  # rotates the session key and the CSRF token
    return Response(UserSerializer(user).data)


@api_view(["POST"])
def logout(request):
    auth_logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
def change_password(request):
    serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)

    user = request.user
    with transaction.atomic():
        before = service.snapshot(user, ["password"])
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        service.record(
            user,
            service.Action.MODIFICATION,
            service.changes(user._meta.model, before, service.snapshot(user, ["password"])),
            module=COMPTES,
            auteur=user,
        )
    # Keeps this session valid; the user's other sessions stop authenticating.
    update_session_auth_hash(request, request.user)
    return Response(status=status.HTTP_204_NO_CONTENT)
