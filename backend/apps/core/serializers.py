from rest_framework import serializers

from .models import BASE_FIELDS


class BaseModelSerializer(serializers.ModelSerializer):
    """ModelSerializer for BaseModel subclasses.

    The creation and modification dates and authors are always read-only: a
    client never decides who wrote a row or when. List them in Meta.fields to
    return them; the authors come out as user ids.
    """

    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        for name in BASE_FIELDS:
            extra_kwargs[name] = {**extra_kwargs.get(name, {}), "read_only": True}
        return extra_kwargs
