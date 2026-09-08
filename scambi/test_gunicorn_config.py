import os
import runpy
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / 'gunicorn.conf.py'
RENDER_CONFIG_PATH = PROJECT_ROOT / 'render.yaml'


class GunicornConfigTests(SimpleTestCase):
    def load_config(self, environment):
        with patch.dict(os.environ, environment, clear=True):
            return runpy.run_path(str(CONFIG_PATH))

    def test_safe_defaults_allow_concurrent_requests_in_one_process(self):
        config = self.load_config({'PORT': '9123'})

        self.assertEqual(config['bind'], '0.0.0.0:9123')
        self.assertEqual(config['workers'], 1)
        self.assertEqual(config['worker_class'], 'gthread')
        self.assertEqual(config['threads'], 4)
        self.assertEqual(config['timeout'], 120)

    def test_threads_and_timeout_can_be_adjusted_within_safe_limits(self):
        config = self.load_config({
            'GUNICORN_THREADS': '6',
            'GUNICORN_TIMEOUT_SECONDS': '180',
        })

        self.assertEqual(config['threads'], 6)
        self.assertEqual(config['timeout'], 180)

    def test_invalid_values_fail_fast(self):
        with self.assertRaises(RuntimeError):
            self.load_config({'GUNICORN_THREADS': 'many'})

        with self.assertRaises(RuntimeError):
            self.load_config({'GUNICORN_TIMEOUT_SECONDS': '999'})

    def test_render_uses_the_versioned_gunicorn_config(self):
        render_config = RENDER_CONFIG_PATH.read_text(encoding='utf-8')

        self.assertIn(
            'gunicorn --config gunicorn.conf.py scambio_sito.wsgi:application',
            render_config,
        )
