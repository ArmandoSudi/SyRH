from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Liveness check: confirms the API answers and PostgreSQL is reachable."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_setting('server_version')")
        database, server_version = cursor.fetchone()
    return Response(
        {
            "status": "ok",
            "database": {
                "vendor": connection.vendor,
                "name": database,
                "version": server_version,
            },
        }
    )
