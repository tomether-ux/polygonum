from django.test.runner import DiscoverRunner


class PolygonumTestRunner(DiscoverRunner):
    """Evita di importare gli script diagnostici ``test_*.py`` in radice."""

    default_test_labels = ('scambi',)

    def build_suite(self, test_labels=None, **kwargs):
        if not test_labels:
            test_labels = self.default_test_labels
        return super().build_suite(test_labels, **kwargs)
