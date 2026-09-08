from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .health import liveness, readiness

urlpatterns = [
    path('health/', liveness, name='health_liveness'),
    path('health/ready/', readiness, name='health_readiness'),
    path('admin/', admin.site.urls),
    path('', include('scambi.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
