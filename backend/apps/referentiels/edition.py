"""Editing the flat reference lists through the API (reference data screens D3 to D9).

Three operations, the three ways history is kept: create a row, correct one in place,
and close a row on a date while opening its successor. Nothing is deleted. The rules
are the models' own: the serializer runs full_clean() and returns its messages per
field, so the API says exactly what Django admin says.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.accounts.roles import module_permission
from apps.core.mixins import AuthorMixin, request_author

from .models import fr

# Set by the system, never by the client: the successor gets its own dates.
DATES = ("date_ouverture", "date_fermeture")


def current_value(field, instance):
    """A writable field's value on a row, as the client would send it back (a key as its
    id), write-only fields included."""
    value = field.get_attribute(instance)
    return None if value is None else field.to_representation(value)


def as_drf_errors(error: DjangoValidationError) -> dict[str, list[str]]:
    """A model ValidationError as DRF field errors, __all__ becoming non_field_errors."""
    if not hasattr(error, "error_dict"):
        return {"non_field_errors": error.messages}
    return {
        ("non_field_errors" if field == "__all__" else field): messages
        for field, messages in error.message_dict.items()
    }


class ModelRulesSerializerMixin:
    """Validates a write with the model's full_clean(), so its constraints and rules
    answer with their own French messages (D5). No rule is copied here."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None:
            instance = self.instance
            for name, value in attrs.items():
                setattr(instance, name, value)
        else:
            instance = self.Meta.model(**attrs)
        try:
            instance.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(as_drf_errors(error)) from error
        return attrs


class ModelPermission(BasePermission):
    """Reading needs access to Référentiels; writing needs the model's Django
    permission: add to create, change to correct, both to close and succeed (D6).

    Other methods are let through so that they answer 405, not 403.
    """

    message = "Vous ne pouvez pas modifier cette liste."
    NEEDS = {"POST": ("add",), "PATCH": ("change",)}

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if not user.has_perm(module_permission("referentiels")):
            return False
        if request.method in SAFE_METHODS:
            return True
        needs = self.NEEDS.get(request.method, ())
        if getattr(view, "action", None) == "successeur":
            needs = ("add", "change")
        opts = view.queryset.model._meta
        return all(user.has_perm(f"{opts.app_label}.{need}_{opts.model_name}") for need in needs)


class SuccesseurSerializer(serializers.Serializer):
    date_effet = serializers.DateField(
        error_messages={"required": "Indiquez la date à partir de laquelle la ligne change."}
    )


class EditionMixin(AuthorMixin, mixins.CreateModelMixin):
    """Write operations for a reference viewset: POST creates, PATCH corrects, and
    POST {id}/successeur/ closes the row on date_effet and opens its successor (D3).

    There is no update (PUT) nor destroy: the router maps only what exists, so those
    answer 405. The writer is the author of the rows and of their audit entries (D7).
    """

    permission_classes = [ModelPermission]

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    # False for a table whose rows have no opening date (sites): no successor.
    REMPLACABLE = True

    @action(detail=True, methods=["post"])
    def successeur(self, request, pk=None):
        if not self.REMPLACABLE:
            raise MethodNotAllowed(request.method)
        current = self.get_object()
        effet = SuccesseurSerializer(data=request.data)
        effet.is_valid(raise_exception=True)
        date_effet = effet.validated_data["date_effet"]

        if current.date_fermeture is not None:
            raise serializers.ValidationError(
                {
                    "date_effet": [
                        "Cette ligne est déjà fermée : corrigez-la ou remplacez la ligne ouverte."
                    ]
                }  # fmt: skip
            )
        if date_effet <= current.date_ouverture:
            raise serializers.ValidationError(
                {
                    "date_effet": [
                        f"Doit être postérieure à l'ouverture ({fr(current.date_ouverture)})."
                    ]
                }
            )

        # The successor starts from the current values, overridden by what was sent (D4).
        reader = self.get_serializer(current)
        writable = [
            name
            for name, field in reader.fields.items()
            if not field.read_only and name not in DATES
        ]
        data = {name: current_value(reader.fields[name], current) for name in writable}
        data.update({k: v for k, v in request.data.items() if k in writable})
        data.update(date_ouverture=date_effet, date_fermeture=None)

        author = request_author(request)
        with transaction.atomic():  # an invalid successor leaves the current row open
            current.date_fermeture = date_effet
            current.modifie_par = author
            try:
                current.save()
            except DjangoValidationError as error:
                raise serializers.ValidationError(as_drf_errors(error)) from error
            successor = self.get_serializer(data=data)
            successor.is_valid(raise_exception=True)
            successor.save(cree_par=author, modifie_par=author)
        return Response(successor.data, status=status.HTTP_201_CREATED)
