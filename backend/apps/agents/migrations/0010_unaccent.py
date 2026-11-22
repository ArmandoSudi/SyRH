from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """PostgreSQL unaccent, for searching names without their accents (agent list D5)."""

    dependencies = [("agents", "0009_piecejointe")]

    operations = [UnaccentExtension()]
