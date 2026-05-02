import hashlib
import logging
from urllib.parse import urlencode

from django.apps import apps
from django.core.cache import cache
from django.db import OperationalError, ProgrammingError
from django.db.models import Count

logger = logging.getLogger(__name__)


class EventCacheService:
    EVENTS_LIST_CACHE_PREFIX = "events:list"
    EVENT_DETAIL_CACHE_PREFIX = "events:detail"
    POPULAR_EVENTS_CACHE_KEY = "events:popular"
    POPULAR_TOURNAMENTS_CACHE_KEY = "tournaments:popular"
    EVENTS_CACHE_VERSION_KEY = "events:cache_version"

    EVENTS_LIST_CACHE_TTL = 60 * 5
    EVENT_DETAIL_CACHE_TTL = 60 * 10
    POPULAR_EVENTS_CACHE_TTL = 60 * 10
    POPULAR_TOURNAMENTS_CACHE_TTL = 60 * 10

    LIST_QUERY_PARAM_KEYS = (
        "category",
        "status",
        "location",
        "search",
        "ordering",
        "page",
        "page_size",
    )

    @classmethod
    def make_events_list_key(cls, request):
        query_items = []
        for key in cls.LIST_QUERY_PARAM_KEYS:
            values = request.query_params.getlist(key)
            for value in values:
                query_items.append((key, value))

        query_string = urlencode(sorted(query_items), doseq=True)
        query_hash = hashlib.md5(query_string.encode("utf-8")).hexdigest()
        return (
            f"{cls.EVENTS_LIST_CACHE_PREFIX}:"
            f"v{cls.get_events_cache_version()}:{query_hash}"
        )

    @classmethod
    def make_event_detail_key(cls, event_id):
        return (
            f"{cls.EVENT_DETAIL_CACHE_PREFIX}:"
            f"v{cls.get_events_cache_version()}:{event_id}"
        )

    @classmethod
    def make_popular_events_key(cls, limit):
        return (
            f"{cls.POPULAR_EVENTS_CACHE_KEY}:"
            f"v{cls.get_events_cache_version()}:limit:{limit}"
        )

    @staticmethod
    def get_cached_response(key):
        try:
            return cache.get(key)
        except Exception:
            logger.exception("Failed to read events cache key %s.", key)
            return None

    @staticmethod
    def set_cached_response(key, data, ttl):
        try:
            cache.set(key, data, ttl)
        except Exception:
            logger.exception("Failed to write events cache key %s.", key)

    @classmethod
    def get_events_cache_version(cls):
        try:
            version = cache.get(cls.EVENTS_CACHE_VERSION_KEY)
            if version is None:
                cache.add(cls.EVENTS_CACHE_VERSION_KEY, 1, None)
                version = cache.get(cls.EVENTS_CACHE_VERSION_KEY, 1)
            return version
        except Exception:
            logger.exception("Failed to read events cache version.")
            return 1

    @classmethod
    def bump_events_cache_version(cls):
        try:
            cache.add(cls.EVENTS_CACHE_VERSION_KEY, 1, None)
            return cache.incr(cls.EVENTS_CACHE_VERSION_KEY)
        except Exception:
            version = (cache.get(cls.EVENTS_CACHE_VERSION_KEY) or 1) + 1
            cache.set(cls.EVENTS_CACHE_VERSION_KEY, version, None)
            return version

    @classmethod
    def invalidate_events_cache(cls):
        try:
            return cls.bump_events_cache_version()
        except Exception:
            logger.exception("Failed to invalidate events cache.")
            return None


class PopularTournamentsService:
    @classmethod
    def get_popular(cls, limit=10):
        try:
            tournament_model = apps.get_model("tournaments", "Tournament")
        except LookupError:
            return []

        try:
            limit = max(1, min(int(limit), 50))
            queryset = tournament_model._default_manager.all()
            fields = {field.name for field in tournament_model._meta.get_fields()}
            if "participants" in fields:
                queryset = queryset.annotate(popularity_count=Count("participants"))
            elif "matches" in fields:
                queryset = queryset.annotate(popularity_count=Count("matches"))
            else:
                queryset = queryset.annotate(popularity_count=Count("id"))

            tournaments = queryset.order_by("-popularity_count", "-id")[:limit]
            return [
                {
                    "id": tournament.id,
                    "title": getattr(
                        tournament,
                        "title",
                        getattr(tournament, "name", str(tournament)),
                    ),
                    "popularity_count": tournament.popularity_count,
                }
                for tournament in tournaments
            ]
        except (OperationalError, ProgrammingError):
            return []
