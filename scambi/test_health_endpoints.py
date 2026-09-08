from pathlib import Path
from unittest.mock import patch

from django.db import connection
from django.db.utils import OperationalError
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class HealthEndpointTests(TestCase):
    def test_liveness_is_public_lightweight_and_not_cached(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('health_liveness'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(len(queries), 0)

    def test_health_endpoints_support_head_but_reject_post(self):
        live_url = reverse('health_liveness')
        ready_url = reverse('health_readiness')

        self.assertEqual(self.client.head(live_url).status_code, 200)
        self.assertEqual(self.client.head(ready_url).status_code, 200)
        self.assertEqual(self.client.post(live_url).status_code, 405)
        self.assertEqual(self.client.post(ready_url).status_code, 405)

    def test_readiness_checks_database_without_exposing_configuration(self):
        response = self.client.get(reverse('health_readiness'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertNotContains(response, 'DATABASE_URL')

    def test_readiness_returns_generic_unavailable_response_on_db_error(self):
        private_detail = 'postgresql://private-user:private-password@db/internal'
        with patch(
            'scambio_sito.health.connection.cursor',
            side_effect=OperationalError(private_detail),
        ):
            response = self.client.get(reverse('health_readiness'))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'unavailable'})
        self.assertNotContains(
            response,
            private_detail,
            status_code=503,
        )


class RenderHealthConfigurationTests(SimpleTestCase):
    def test_render_uses_lightweight_liveness_endpoint(self):
        render_config = (PROJECT_ROOT / 'render.yaml').read_text(
            encoding='utf-8'
        )

        self.assertIn('healthCheckPath: /health/', render_config)
        self.assertNotIn('healthCheckPath: /\n', render_config)
