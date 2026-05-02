from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class CeleryConfigTests(SimpleTestCase):
    def test_celery_app_import_works(self):
        from config.celery import app

        self.assertEqual(app.main, "eventhub")

    def test_test_settings_enable_eager_tasks(self):
        settings_path = Path(__file__).resolve().parents[3] / "config/settings/test.py"
        content = settings_path.read_text()

        self.assertIn("CELERY_TASK_ALWAYS_EAGER = True", content)
        self.assertIn("CELERY_TASK_EAGER_PROPAGATES = True", content)

    def test_base_settings_use_redis_url_for_celery(self):
        self.assertEqual(settings.CELERY_BROKER_URL, settings.REDIS_URL)
        self.assertEqual(settings.CELERY_RESULT_BACKEND, settings.REDIS_URL)
