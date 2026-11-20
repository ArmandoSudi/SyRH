"""Editing the flat reference lists through the API (reference data screens D3 to D9).

Three operations, the three ways history is kept: create a row, correct one in place,
and close a row on a date while opening its successor. Nothing is deleted. The rules
are the models' own: the serializer runs full_clean() and returns its messages per
field, so the API says exactly what Django admin says.
"""

from dataclasses import dataclass, field

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Model
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.accounts.roles import module_permission
from apps.core.mixins import AuthorMixin, request_author

from .models import UniteOrganisationnelle, fr, still_open_after

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
        action_name = getattr(view, "action", None)
        if request.method in SAFE_METHODS and action_name != "suite":
            return True
        needs = self.NEEDS.get(request.method, ())
        if action_name in ("successeur", "suite"):  # the preview needs the right to replace
            needs = ("add", "change")
        opts = view.queryset.model._meta
        return all(user.has_perm(f"{opts.app_label}.{need}_{opts.model_name}") for need in needs)


# What follows a parent when it is replaced at a date: the related names of its child
# rows, per model (tree reference screens D5). Sites carry nothing (D6).
SUITES: dict[str, tuple[str, ...]] = {
    "uniteorganisationnelle": ("enfants",),
    "categorie": ("grades",),
    "grade": ("echelons",),
    "typedocument": ("pieces_requises", "motifs_sortie", "types_suspension"),
}

# How a kind of row is counted in the preview, singular and plural; units by their type (D9).
GENRES_UNITES = {
    "direction": ("direction", "directions"),
    "departement": ("département", "départements"),
    "service": ("service", "services"),
    "bureau": ("bureau", "bureaux"),
}


@dataclass
class Suivant:
    """A child row that follows its parent, the key pointing to that parent, and its own
    followers."""

    row: Model
    cle: str
    suivants: list["Suivant"] = field(default_factory=list)


def suivants(row: Model, jour, bloquants: list[Model]) -> list[Suivant]:
    """The rows still open after jour that follow row, down the whole subtree. A child
    opening on or after jour cannot be carried over: it goes to bloquants (D7)."""
    found = []
    for related in SUITES.get(row._meta.model_name, ()):
        cle = row._meta.get_field(related).field.name
        for child in getattr(row, related).filter(still_open_after(jour)).order_by("pk"):
            if child.date_ouverture >= jour:
                bloquants.append(child)
            else:
                found.append(Suivant(child, cle, suivants(child, jour, bloquants)))
    return found


def a_plat(liste: list[Suivant]):
    for suivant in liste:
        yield suivant
        yield from a_plat(suivant.suivants)


def genre(row: Model) -> tuple[str, str]:
    if isinstance(row, UniteOrganisationnelle):
        return GENRES_UNITES[row.type]
    return str(row._meta.verbose_name), str(row._meta.verbose_name_plural)


def errors_on(row: Model, error: DjangoValidationError) -> serializers.ValidationError:
    """A child's refusal, naming the row so the user knows which one to fix (D4)."""
    messages = [message for messages in as_drf_errors(error).values() for message in messages]
    return serializers.ValidationError(
        {"non_field_errors": [f"{row} : {message}" for message in messages]}
    )


def fermer(liste: list[Suivant], jour, author) -> None:
    """Close the followers on jour, deepest first: a parent cannot close before them."""
    for suivant in liste:
        fermer(suivant.suivants, jour, author)
        row = suivant.row
        row.date_fermeture = jour
        row.modifie_par = author
        try:
            row.save()
        except DjangoValidationError as error:
            raise errors_on(row, error) from error


def recopier(liste: list[Suivant], parent: Model, jour, author) -> None:
    """Reopen a copy of each follower under its new parent from jour, top-down."""
    for suivant in liste:
        old = suivant.row
        copie = type(old)._base_manager.get(pk=old.pk)
        copie.pk = None
        copie._state.adding = True
        setattr(copie, suivant.cle, parent)
        copie.date_ouverture = jour
        copie.date_fermeture = None
        copie.cree_par = copie.modifie_par = author
        try:
            copie.full_clean()
            copie.save()
        except DjangoValidationError as error:
            raise errors_on(old, error) from error
        recopier(suivant.suivants, copie, jour, author)


def bloquants_error(bloquants: list[Model]) -> serializers.ValidationError:
    names = ", ".join(str(row) for row in bloquants[:5])
    return serializers.ValidationError(
        {
            "date_effet": [
                f"Des lignes rattachées ouvrent à cette date ou après : {names}. "
                "Corrigez-les ou fermez-les d'abord."
            ]
        }
    )


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

        bloquants: list[Model] = []
        followers = suivants(current, date_effet, bloquants)
        if bloquants:
            raise bloquants_error(bloquants)

        author = request_author(request)
        # One act: if anything is refused, nothing is closed and nothing is created (D4).
        with transaction.atomic():
            fermer(followers, date_effet, author)
            current.date_fermeture = date_effet
            current.modifie_par = author
            try:
                current.save()
            except DjangoValidationError as error:
                raise serializers.ValidationError(as_drf_errors(error)) from error
            successor = self.get_serializer(data=data)
            successor.is_valid(raise_exception=True)
            successor.save(cree_par=author, modifie_par=author)
            recopier(followers, successor.instance, date_effet, author)
        return Response(successor.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def suite(self, request, pk=None):
        """What a replacement on date_effet would carry over, by kind, and what blocks it
        (D9)."""
        if not self.REMPLACABLE:
            raise MethodNotAllowed(request.method)
        current = self.get_object()
        effet = SuccesseurSerializer(data=request.query_params)
        effet.is_valid(raise_exception=True)
        bloquants: list[Model] = []
        followers = list(a_plat(suivants(current, effet.validated_data["date_effet"], bloquants)))
        counts: dict[tuple[str, str], int] = {}
        for suivant in followers:
            kind = genre(suivant.row)
            counts[kind] = counts.get(kind, 0) + 1
        return Response(
            {
                "total": len(followers),
                "par_genre": [
                    {"libelle": plural if n > 1 else singular, "nombre": n}
                    for (singular, plural), n in counts.items()
                ],
                "bloquants": [str(row) for row in bloquants],
            }
        )
