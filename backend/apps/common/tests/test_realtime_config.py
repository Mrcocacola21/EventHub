from pathlib import Path

from django.test import SimpleTestCase


class RealtimeInfrastructureConfigTests(SimpleTestCase):
    def backend_root(self):
        return Path(__file__).resolve().parents[3]

    def repo_root(self):
        backend_root = self.backend_root()
        if backend_root.name == "backend":
            return backend_root.parent
        return backend_root

    def test_channels_dependencies_are_declared(self):
        requirements = self.backend_root() / "requirements.txt"
        content = requirements.read_text()

        self.assertIn("channels==", content)
        self.assertIn("channels-redis==", content)
        self.assertIn("daphne==", content)

    def test_channel_layer_uses_in_memory_backend_in_tests(self):
        test_settings = self.backend_root() / "config" / "settings" / "test.py"
        content = test_settings.read_text()

        self.assertIn("channels.layers.InMemoryChannelLayer", content)

    def test_base_settings_define_redis_channel_layer(self):
        base_settings = self.backend_root() / "config" / "settings" / "base.py"
        content = base_settings.read_text()

        self.assertIn('"channels"', content)
        self.assertIn("channels_redis.core.RedisChannelLayer", content)
        self.assertIn("CHANNEL_REDIS_URL", content)

    def test_env_example_separates_channel_redis_database(self):
        env_example = self.backend_root() / ".env.example"
        content = env_example.read_text()

        self.assertIn("REDIS_URL=redis://redis:6379/0", content)
        self.assertIn("CACHE_URL=redis://redis:6379/1", content)
        self.assertIn("CHANNEL_REDIS_URL=redis://redis:6379/2", content)

    def test_asgi_uses_protocol_type_router(self):
        asgi = self.backend_root() / "config" / "asgi.py"
        content = asgi.read_text()

        self.assertIn("ProtocolTypeRouter", content)
        self.assertIn('"http": django_asgi_app', content)
        self.assertIn('"websocket": JWTAuthMiddlewareStack', content)
        self.assertLess(
            content.index("django_asgi_app = get_asgi_application()"),
            content.index("from apps.notifications.middleware"),
        )

    def test_docker_compose_contains_celery_services(self):
        compose = self.repo_root() / "docker-compose.yml"
        if not compose.exists():
            self.skipTest("docker-compose.yml is outside the backend container volume.")

        content = compose.read_text()

        self.assertIn("celery_worker:", content)
        self.assertIn("celery_beat:", content)
        self.assertIn("celery -A config worker -l info", content)
        self.assertIn(
            "celery -A config beat -l info "
            "--scheduler django_celery_beat.schedulers:DatabaseScheduler",
            content,
        )
