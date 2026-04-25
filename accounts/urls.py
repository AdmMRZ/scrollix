from django.urls import path
from .views import RegisterView, CustomLoginView, CustomLogoutView, LibraryView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('library/', LibraryView.as_view(), name='library'),
]
