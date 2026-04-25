"""
Repository layer — all database queries live here.
Views and services import from here; they never call .filter() directly.
"""
from __future__ import annotations
from typing import Optional
from django.db.models import QuerySet, Prefetch
from django.conf import settings

from .models import CachedManga, CachedChapter, Genre, Bookmark, ReadHistory


# ─── Manga ────────────────────────────────────────────────────────────────────

def get_manga_by_mangadex_id(mangadex_id: str) -> Optional[CachedManga]:
    """Return a cached manga or None if not in the DB."""
    try:
        return CachedManga.objects.prefetch_related('genres').get(
            mangadex_id=mangadex_id
        )
    except CachedManga.DoesNotExist:
        return None


def get_latest_updated_manga(limit: int = 20) -> QuerySet:
    """Manga ordered by most recently cached (proxy for update time)."""
    return (
        CachedManga.objects
        .prefetch_related('genres')
        .order_by('-cached_at')[:limit]
    )


def get_popular_manga(limit: int = 10) -> QuerySet:
    """Manga ordered by follow count — used for homepage featured."""
    return (
        CachedManga.objects
        .prefetch_related('genres')
        .order_by('-follow_count')[:limit]
    )


def search_manga_in_cache(
    query: str = '',
    genre_include_ids: list[str] | None = None,
    genre_exclude_ids: list[str] | None = None,
    status: str = '',
    sort: str = '-cached_at',
) -> QuerySet:
    """
    Filter manga from local cache. Used as fallback / supplement to API search.
    All parameters are optional.
    """
    qs = CachedManga.objects.prefetch_related('genres').all()

    if query:
        qs = qs.filter(title__icontains=query)

    if status:
        qs = qs.filter(status=status)

    if genre_include_ids:
        for gid in genre_include_ids:
            qs = qs.filter(genres__mangadex_id=gid)

    if genre_exclude_ids:
        qs = qs.exclude(genres__mangadex_id__in=genre_exclude_ids)

    valid_sorts = {
        'title': 'title',
        '-title': '-title',
        'latest': '-cached_at',
        'popular': '-follow_count',
        'year': 'year',
        '-year': '-year',
    }
    qs = qs.order_by(valid_sorts.get(sort, '-cached_at'))
    return qs.distinct()


# ─── Chapters ─────────────────────────────────────────────────────────────────

def get_chapters_for_manga(
    manga: CachedManga, language: str = 'en'
) -> QuerySet:
    """All chapters for a manga in a given language, ordered by chapter number."""
    return (
        manga.chapters
        .filter(language=language)
        .order_by('published_at')
    )


def get_chapter_by_mangadex_id(chapter_id: str) -> Optional[CachedChapter]:
    try:
        return CachedChapter.objects.select_related('manga').get(
            mangadex_id=chapter_id
        )
    except CachedChapter.DoesNotExist:
        return None


def get_adjacent_chapters(
    chapter: CachedChapter,
) -> dict[str, Optional[CachedChapter]]:
    """
    Return the previous and next chapters in the same manga/language feed.
    Ordered by published_at ascending.
    """
    feed = list(
        chapter.manga.chapters
        .filter(language=chapter.language)
        .order_by('published_at')
        .values_list('id', 'mangadex_id')
    )

    ids = [row[0] for row in feed]
    try:
        idx = ids.index(chapter.id)
    except ValueError:
        return {'prev': None, 'next': None}

    prev_obj = None
    next_obj = None

    if idx > 0:
        prev_id = feed[idx - 1][0]
        prev_obj = CachedChapter.objects.get(id=prev_id)

    if idx < len(feed) - 1:
        next_id = feed[idx + 1][0]
        next_obj = CachedChapter.objects.get(id=next_id)

    return {'prev': prev_obj, 'next': next_obj}


def chapters_are_stale(manga: CachedManga) -> bool:
    """True if the chapter cache is missing or expired for this manga."""
    chapter = manga.chapters.order_by('-cached_at').first()
    if chapter is None:
        return True
    return chapter.is_stale(settings.CACHE_TTL_CHAPTERS)


# ─── Genres ───────────────────────────────────────────────────────────────────

def get_all_genres() -> QuerySet:
    return Genre.objects.all().order_by('name')


def get_genres_by_ids(ids: list[str]) -> QuerySet:
    return Genre.objects.filter(mangadex_id__in=ids)


# ─── Bookmarks ────────────────────────────────────────────────────────────────

def get_user_bookmark(user, manga: CachedManga) -> Optional[Bookmark]:
    try:
        return Bookmark.objects.get(user=user, manga=manga)
    except Bookmark.DoesNotExist:
        return None


def get_user_bookmarks(user, list_type: str = '') -> QuerySet:
    qs = Bookmark.objects.filter(user=user).select_related('manga').prefetch_related(
        'manga__genres'
    )
    if list_type:
        qs = qs.filter(list_type=list_type)
    return qs.order_by('-updated_at')


# ─── Read History ─────────────────────────────────────────────────────────────

def get_user_read_history(user, limit: int = 50) -> QuerySet:
    return (
        ReadHistory.objects
        .filter(user=user)
        .select_related('chapter', 'manga')
        .order_by('-read_at')[:limit]
    )


def has_user_read_chapter(user, chapter: CachedChapter) -> bool:
    return ReadHistory.objects.filter(user=user, chapter=chapter).exists()
