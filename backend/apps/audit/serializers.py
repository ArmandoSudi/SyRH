from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from apps.accounts.roles import MODULES

from .models import COMPTES, EntreeAudit

# Every scope an entry can carry, with its French label.
SCOPES: dict[str, str] = {**MODULES, COMPTES: "Comptes"}

SYSTEM_AUTHOR = "Système"


def table_label(content_type: ContentType) -> str:
    model = content_type.model_class()
    label = model._meta.verbose_name if model is not None else content_type.model
    return str(label)[:1].upper() + str(label)[1:]


class EntreeAuditSerializer(serializers.ModelSerializer):
    auteur = serializers.SerializerMethodField()
    action_libelle = serializers.CharField(source="get_action_display")
    module_libelle = serializers.SerializerMethodField()
    table = serializers.SerializerMethodField()

    class Meta:
        model = EntreeAudit
        fields = [
            "id",
            "date",
            "auteur",
            "action",
            "action_libelle",
            "module",
            "module_libelle",
            "table",
            "objet_id",
            "objet_libelle",
        ]
        read_only_fields = fields

    def get_auteur(self, entry) -> dict:
        user = entry.auteur
        if user is None:
            return {"id": None, "nom": SYSTEM_AUTHOR}
        return {"id": user.pk, "nom": user.get_full_name() or user.get_username()}

    def get_module_libelle(self, entry) -> str:
        return SCOPES.get(entry.module, entry.module)

    def get_table(self, entry) -> dict:
        content_type = entry.table
        return {
            "cle": f"{content_type.app_label}.{content_type.model}",
            "libelle": table_label(content_type),
        }


class EntreeAuditDetailSerializer(EntreeAuditSerializer):
    class Meta(EntreeAuditSerializer.Meta):
        fields = [*EntreeAuditSerializer.Meta.fields, "changements"]
        read_only_fields = fields


class FiltresSerializer(serializers.Serializer):
    """Query string of the list (D24). Errors come back per field."""

    date_debut = serializers.DateField(required=False)
    date_fin = serializers.DateField(required=False)
    auteur = serializers.CharField(required=False, max_length=150)
    module = serializers.ChoiceField(choices=list(SCOPES), required=False)
    action = serializers.ChoiceField(choices=EntreeAudit.Action.choices, required=False)
    table = serializers.CharField(required=False)
    objet = serializers.IntegerField(required=False)

    def validate_table(self, value):
        app_label, _, model = value.partition(".")
        try:
            return ContentType.objects.get_by_natural_key(app_label, model)
        except ContentType.DoesNotExist as error:
            raise serializers.ValidationError("Table inconnue.") from error

    def validate(self, attrs):
        if "objet" in attrs and "table" not in attrs:
            raise serializers.ValidationError({"objet": ["Précisez aussi la table."]})
        if (
            "date_debut" in attrs
            and "date_fin" in attrs
            and attrs["date_debut"] > attrs["date_fin"]
        ):
            raise serializers.ValidationError(
                {"date_fin": ["La date de fin précède la date de début."]}
            )
        return attrs
