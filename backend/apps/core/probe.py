"""Test-only BaseModel and its API and admin classes. Imported by tests only.

Probe has no migration (managed = False): ProbeTestCase creates its table
inside each test class's transaction, which rolls it back afterwards.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.test import TestCase
from django.utils import timezone
from rest_framework import viewsets

from .admin import BaseModelAdmin
from .mixins import AuthorMixin
from .models import BASE_FIELDS, BaseModel
from .serializers import BaseModelSerializer


class Probe(BaseModel):
    module = "referentiels"

    nom = models.CharField("nom", max_length=50)
    montant = models.DecimalField("montant", max_digits=10, decimal_places=2, null=True)
    date_effet = models.DateField("date d'effet", null=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="responsable",
        on_delete=models.PROTECT,
        null=True,
        related_name="+",
    )

    class Meta:
        app_label = "core"
        managed = False
        db_table = "core_test_probe"
        verbose_name = "sonde"

    def __str__(self):
        return self.nom


class ProbeSerializer(BaseModelSerializer):
    class Meta:
        model = Probe
        fields = ["id", "nom", *BASE_FIELDS]


class ProbeViewSet(AuthorMixin, viewsets.ModelViewSet):
    queryset = Probe.objects.all()
    serializer_class = ProbeSerializer


class ProbeAdmin(BaseModelAdmin, admin.ModelAdmin):
    readonly_fields = ["nom"]


class ProbeTestCase(TestCase):
    """Creates the Probe table inside the class transaction, rolled back after."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            editor.create_model(Probe)
        # Probe's content type lives in the class transaction too, so each test
        # can write audit entries; drop any id cached by a previous class.
        ContentType.objects.clear_cache()
        ContentType.objects.get_for_model(Probe)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        ContentType.objects.clear_cache()

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice = User.objects.create_user("alice", password="x")
        cls.bruno = User.objects.create_user("bruno", password="x")

    def make_old(self, probe):
        """Push date_modification into the past, so a later save visibly moves it.

        Goes through _base_manager: Probe.objects refuses unaudited updates.
        """
        old = timezone.now() - timedelta(days=1)
        Probe._base_manager.filter(pk=probe.pk).update(date_modification=old)
        probe.refresh_from_db()
        return old
