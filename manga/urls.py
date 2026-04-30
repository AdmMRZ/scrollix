from django.urls import path
from . import views, apis
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('browse/', views.BrowseView.as_view(), name='browse'),
    path('manga/<str:mangadex_id>/', views.MangaDetailView.as_view(), name='manga-detail'),
    path('manga/<str:mangadex_id>/chapters/all/', views.ChapterListAllView.as_view(), name='chapters-all'),
    path('read/<str:chapter_id>/', views.ReaderView.as_view(), name='reader'),
    path('api/bookmark/', apis.ToggleBookmarkView.as_view(), name='toggle-bookmark'),
    path('api/img-proxy/', apis.ImageProxyView.as_view(), name='img-proxy'),
    path('api/manga/<str:mangadex_id>/top-chapters/', views.MangaTopChaptersAPIView.as_view(), name='api-top-chapters'),
]
