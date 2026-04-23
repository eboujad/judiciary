"""
Master URL configuration — Gambia Judiciary E-Filing System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

API_V1 = 'api/v1/'

urlpatterns = [
    # Root → redirect to Swagger UI
    path('', RedirectView.as_view(url='/api/docs/', permanent=False)),

    # Admin
    path('admin/', admin.site.urls),

    # API v1
    path(API_V1 + 'auth/', include('apps.users.urls')),
    path(API_V1 + 'firms/', include('apps.firms.urls')),
    path(API_V1 + 'cases/', include('apps.cases.urls')),
    path(API_V1 + 'documents/', include('apps.documents.urls')),
    path(API_V1 + 'payments/', include('apps.payments.urls')),
    path(API_V1 + 'audit/', include('apps.audit.urls')),

    # OpenAPI Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
