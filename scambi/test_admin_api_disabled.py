from django.conf import settings
from django.test import SimpleTestCase


class AdminApiDisabledTests(SimpleTestCase):
    def test_legacy_admin_api_endpoints_are_not_routable(self):
        requests = (
            ('get', '/api/admin/annunci-pending/'),
            ('post', '/api/admin/modera/1/'),
            ('get', '/api/admin/stats/'),
        )

        for method, path in requests:
            with self.subTest(path=path):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 404)

    def test_public_gestionale_origin_is_not_allowed_by_cors(self):
        self.assertNotIn(
            'https://gestionale-sigma.vercel.app',
            settings.CORS_ALLOWED_ORIGINS,
        )

    def test_static_admin_bearer_token_is_no_longer_configured(self):
        self.assertFalse(hasattr(settings, 'ADMIN_GESTIONALE_TOKEN'))
