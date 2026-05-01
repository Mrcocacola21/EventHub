import shutil
import tempfile

from django.test import override_settings


class TempMediaRootMixin:
    @classmethod
    def setUpClass(cls):
        cls._temp_media_root = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media_root, ignore_errors=True)
