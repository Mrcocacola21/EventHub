from rest_framework.routers import DefaultRouter

from .views import EventCategoryViewSet, EventViewSet

router = DefaultRouter()
router.register("event-categories", EventCategoryViewSet, basename="event-category")
router.register("events", EventViewSet, basename="event")

urlpatterns = router.urls
