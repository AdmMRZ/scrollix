from django.contrib import admin
from .models import Genre, CachedManga, CachedChapter, Bookmark, ReadHistory


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'mangadex_id']
    search_fields = ['name']


@admin.register(CachedManga)
class CachedMangaAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'author', 'follow_count', 'cached_at']
    list_filter = ['status', 'content_rating']
    search_fields = ['title', 'mangadex_id']
    readonly_fields = ['cached_at']
    filter_horizontal = ['genres']


@admin.register(CachedChapter)
class CachedChapterAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'chapter_number', 'language', 'pages_count', 'published_at']
    list_filter = ['language']
    search_fields = ['manga__title', 'mangadex_id']
    readonly_fields = ['cached_at']


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'manga', 'list_type', 'updated_at']
    list_filter = ['list_type']


@admin.register(ReadHistory)
class ReadHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'chapter', 'read_at']
