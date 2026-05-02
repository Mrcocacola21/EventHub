from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class CacheSettingsTests(SimpleTestCase):
    def test_cache_settings_are_configured(self):
        self.assertIn("default", settings.CACHES)
        self.assertIn("BACKEND", settings.CACHES["default"])

    def test_test_settings_use_locmem_cache(self):
        settings_path = Path(__file__).resolve().parents[3] / "config/settings/test.py"
        content = settings_path.read_text()

        self.assertIn("django.core.cache.backends.locmem.LocMemCache", content)

    def test_cache_url_setting_exists(self):
        self.assertTrue(hasattr(settings, "CACHE_URL"))
