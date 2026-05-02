from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.bookings.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/", include("apps.tickets.urls")),
    path("api/", include("apps.events.urls")),
    path("api/", include("apps.users.urls")),
    path("api/health/", include("apps.common.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
