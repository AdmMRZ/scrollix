from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('manga.urls')),
    path('accounts/', include('accounts.urls')),
]
