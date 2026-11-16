from django.test import TestCase
from django.urls import reverse


class HealthTests(TestCase):
    def test_health_reports_postgresql(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["database"]["vendor"], "postgresql")
