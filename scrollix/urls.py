from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from . import views as project_views

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('manga.urls')),
    path('accounts/', include('accounts.urls')),
    path('service-unavailable/', project_views.service_unavailable, name='service-unavailable'),
]

handler400 = 'scrollix.views.error_400'
handler403 = 'scrollix.views.error_403'
handler404 = 'scrollix.views.error_404'
handler500 = 'scrollix.views.error_500'
