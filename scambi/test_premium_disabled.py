from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve, reverse

from .views import premium_unavailable


class PremiumDisabledTests(SimpleTestCase):
    def test_pricing_page_contains_no_payment_integration(self):
        html = render_to_string(
            'scambi/pricing.html',
            {'user': AnonymousUser()},
        )

        self.assertNotIn('paypal.com', html.lower())
        self.assertIn('non accetta pagamenti', html)

    def test_legacy_premium_urls_are_inert(self):
        for path in (
            '/premium/checkout/',
            '/premium/success/',
            '/premium/cancel/',
        ):
            self.assertIs(resolve(path).func, premium_unavailable)

    def test_legacy_premium_endpoint_only_redirects(self):
        request = RequestFactory().get('/premium/success/')

        with patch('scambi.views.messages.info'):
            response = premium_unavailable(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('pricing'))
