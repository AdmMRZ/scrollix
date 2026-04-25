from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('browse/', views.BrowseView.as_view(), name='browse'),
    path('manga/<str:mangadex_id>/', views.MangaDetailView.as_view(), name='manga-detail'),
    path('read/<str:chapter_id>/', views.ReaderView.as_view(), name='reader'),
    path('api/bookmark/', views.ToggleBookmarkView.as_view(), name='toggle-bookmark'),
    path('library/', views.LibraryView.as_view(), name='library'),
]
