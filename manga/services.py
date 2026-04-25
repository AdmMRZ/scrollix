from __future__ import annotations
import logging
import time
import urllib.parse
from typing import Optional
import requests
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from .models import CachedManga, CachedChapter, Genre, Bookmark, ReadHistory
from . import selectors
from django.core.cache import cache
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)
MANGADEX_BASE = settings.MANGADEX_API_BASE
REQUEST_TIMEOUT = 10
REQUEST_HEADERS = {
    'User-Agent': 'Scrollix/1.0 (personal manga reader; contact via github)',
}

def _api_get(path: str, params: dict = None) -> dict | None:
    url = f"{MANGADEX_BASE}{path}"
    try:
        response = requests.get(
            url,
            params=params,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 429:
            logger.warning("MangaDex rate limit hit — sleeping 2s")
            time.sleep(2)
            response = requests.get(url, params=params, headers=REQUEST_HEADERS,
                                    timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.error("MangaDex API error for %s: %s", path, exc)
        return None
def fetch_manga_detail(mangadex_id: str) -> dict | None:
    data = _api_get(f"/manga/{mangadex_id}", params={
        'includes[]': ['author', 'artist', 'cover_art'],
    })
    return data.get('data') if data else None
    
def fetch_manga_list(params: dict) -> list[dict]:
    data = _api_get('/manga', params=params)
    return data.get('data', []) if data else []
def fetch_chapter_feed(mangadex_id: str, language: str = 'en') -> list[dict]:
    chapters = []
    offset = 0
    limit = 500
    while True:
        data = _api_get(f"/manga/{mangadex_id}/feed", params={
            'translatedLanguage[]': language,
            'order[chapter]': 'asc',
            'limit': limit,
            'offset': offset,
            'includes[]': ['scanlation_group'],
        })
        if not data:
            break
        batch = data.get('data', [])
        chapters.extend(batch)
        total = data.get('total', 0)
        offset += limit
        if offset >= total:
            break
    return chapters

def fetch_chapter_pages(chapter_id: str) -> dict | None:
    data = _api_get(f"/at-home/server/{chapter_id}")
    if not data:
        logger.error("fetch_chapter_pages: no data returned for chapter %s", chapter_id)
        return None
    chapter_data = data.get('chapter', {})
    pages = chapter_data.get('data', [])
    pages_saver = chapter_data.get('dataSaver', [])
    base_url = data.get('baseUrl', '')
    hash_ = chapter_data.get('hash', '')
    logger.info(
        "fetch_chapter_pages: chapter=%s base_url=%s hash=%s pages=%d saver=%d",
        chapter_id, base_url, hash_, len(pages), len(pages_saver)
    )
    return {
        'base_url': base_url,
        'hash': hash_,
        'pages': pages,
        'pages_saver': pages_saver,
    }

def fetch_tags() -> list[dict]:
    data = _api_get('/manga/tag')
    return data.get('data', []) if data else []

def fetch_popular_manga(limit: int = 20) -> list[dict]:
    return fetch_manga_list({
        'order[followedCount]': 'desc',
        'limit': limit,
        'includes[]': ['cover_art', 'author'],
        'contentRating[]': ['safe', 'suggestive'],
        'availableTranslatedLanguage[]': 'en',
    })

def fetch_latest_manga(limit: int = 24) -> list[dict]:
    return fetch_manga_list({
        'order[latestUploadedChapter]': 'desc',
        'limit': limit,
        'includes[]': ['cover_art', 'author'],
        'contentRating[]': ['safe', 'suggestive'],
        'availableTranslatedLanguage[]': 'en',
    })

def build_page_urls(at_home: dict, quality: str = 'data', use_proxy: bool = None) -> list[str]:
    if use_proxy is None:
        use_proxy = getattr(settings, 'USE_IMAGE_PROXY', False)
    
    base = at_home['base_url']
    hash_ = at_home['hash']
    if quality == 'data-saver':
        files = at_home.get('pages_saver') or at_home.get('pages', [])
        quality_path = 'data-saver' if at_home.get('pages_saver') else 'data'
    else:
        files = at_home.get('pages', [])
        quality_path = 'data'
    direct_urls = [f"{base}/{quality_path}/{hash_}/{f}" for f in files]
    if use_proxy:
        return [
            f"/api/img-proxy/?url={urllib.parse.quote(u, safe='')}"
            for u in direct_urls
        ]
    return direct_urls

def _parse_cover_url(manga_data: dict) -> str:
    mangadex_id = manga_data.get('id', '')
    for rel in manga_data.get('relationships', []):
        if rel.get('type') == 'cover_art':
            filename = rel.get('attributes', {}).get('fileName', '')
            if filename:
                return f"https://uploads.mangadex.org/covers/{mangadex_id}/{filename}.256.jpg"
    return ''

def fetch_manga_statistics(mangadex_ids: list[str]) -> dict:
    if not mangadex_ids:
        return {}
    data = _api_get('/statistics/manga', params={'manga[]': mangadex_ids})
    if not data:
        return {}
    return data.get('statistics', {})

def _save_manga_to_cache(manga_data: dict, stats: dict = None) -> CachedManga:
    attrs = manga_data.get('attributes', {})
    mangadex_id = manga_data.get('id', '')
    
    follow_count = 0
    if stats and mangadex_id in stats:
        follow_count = stats[mangadex_id].get('follows', 0)

    lang = attrs.get('originalLanguage', '')
    if lang == 'ja':
        custom_type = 'Manga'
    elif lang == 'ko':
        custom_type = 'Manhwa'
    elif 'zh' in lang:
        custom_type = 'Manhua'
    else:
        custom_type = 'Manga'

    titles = attrs.get('title', {})
    title = titles.get('en')
    if not title:
        for alt in attrs.get('altTitles', []):
            if 'en' in alt:
                title = alt['en']
                break
    if not title:
        title = (
            titles.get('ja-ro') or 
            titles.get('ja') or
            next(iter(titles.values()), 'Unknown')
        )
    alt_titles = []
    for alt in attrs.get('altTitles', []):
        for lang, val in alt.items():
            if val and val != title:
                alt_titles.append(val)
    desc = attrs.get('description', {})
    description = desc.get('en', '') or next(iter(desc.values()), '')
    author = ''
    artist = ''
    for rel in manga_data.get('relationships', []):
        name = rel.get('attributes', {}).get('name', '')
        if rel.get('type') == 'author' and not author:
            author = name
        elif rel.get('type') == 'artist' and not artist:
            artist = name
    manga, _ = CachedManga.objects.update_or_create(
        mangadex_id=mangadex_id,
        defaults={
            'title': title[:500],
            'alt_titles': alt_titles[:10],
            'description': description,
            'author': author[:300],
            'artist': artist[:300],
            'status': attrs.get('status', '')[:20],
            'custom_type': custom_type,
            'cover_url': _parse_cover_url(manga_data),
            'year': attrs.get('year'),
            'content_rating': attrs.get('contentRating', '')[:30],
            'last_chapter': str(attrs.get('lastChapter') or '')[:20],
            'follow_count': follow_count,
        },
    )
    tag_ids = []
    for tag in attrs.get('tags', []):
        tag_id = tag.get('id', '')
        tag_name = tag.get('attributes', {}).get('name', {}).get('en', '')
        if tag_id and tag_name:
            genre, _ = Genre.objects.get_or_create(
                mangadex_id=tag_id,
                defaults={'name': tag_name, 'slug': slugify(tag_name)},
            )
            tag_ids.append(genre.pk)
    manga.genres.set(tag_ids)
    return manga
def _save_chapters_to_cache(
    manga: CachedManga, chapters_data: list[dict]
) -> None:
    for ch in chapters_data:
        attrs = ch.get('attributes', {})
        chapter_id = ch.get('id', '')
        if not chapter_id:
            continue
        scanlation = ''
        for rel in ch.get('relationships', []):
            if rel.get('type') == 'scanlation_group':
                scanlation = rel.get('attributes', {}).get('name', '') or ''
                break
        published_str = attrs.get('publishAt') or attrs.get('createdAt')
        published_at = None
        if published_str:
            published_at = parse_datetime(published_str)
        CachedChapter.objects.update_or_create(
            mangadex_id=chapter_id,
            defaults={
                'manga': manga,
                'chapter_number': str(attrs.get('chapter') or '')[:20],
                'volume': str(attrs.get('volume') or '')[:20],
                'title': str(attrs.get('title') or '')[:500],
                'language': attrs.get('translatedLanguage', 'en')[:10],
                'pages_count': attrs.get('pages', 0),
                'published_at': published_at,
                'scanlation_group': scanlation[:300],
            },
        )
def get_or_fetch_manga(mangadex_id: str) -> CachedManga | None:
    manga = selectors.get_manga_by_mangadex_id(mangadex_id)
    if manga is None or manga.is_stale():
        raw = fetch_manga_detail(mangadex_id)
        if raw:
            manga = _save_manga_to_cache(raw)
        elif manga is None:
            return None
    return manga
def get_or_fetch_chapters(manga: CachedManga, language: str = 'en') -> list:
    if selectors.chapters_are_stale(manga):
        chapters_data = fetch_chapter_feed(manga.mangadex_id, language)
        if chapters_data:
            _save_chapters_to_cache(manga, chapters_data)
    return list(selectors.get_chapters_for_manga(manga, language))
def get_reader_data(chapter_id: str) -> dict | None:
    chapter = selectors.get_chapter_by_mangadex_id(chapter_id)
    if chapter is None:
        logger.warning("get_reader_data: chapter %s not in cache", chapter_id)
        return None
    at_home = fetch_chapter_pages(chapter_id)
    if not at_home:
        return None
    pages = build_page_urls(at_home, quality='data-saver')
    if not pages:
        logger.warning("get_reader_data: 0 pages built for chapter %s", chapter_id)
    adjacent = selectors.get_adjacent_chapters(chapter)
    return {
        'manga': chapter.manga,
        'chapter': chapter,
        'pages': pages,
        'at_home_base': at_home.get('base_url', ''),
        'prev_chapter': adjacent['prev'],
        'next_chapter': adjacent['next'],
        'page_count': len(pages),
    }

def get_homepage_data() -> dict:
    featured_ids = cache.get('home_featured_ids')
    latest_ids = cache.get('home_latest_ids')

    if not featured_ids:
        raw_popular = fetch_popular_manga(limit=6)
        featured_ids = [m['id'] for m in raw_popular]
        stats = fetch_manga_statistics(featured_ids)
        for m in raw_popular:
            _save_manga_to_cache(m, stats=stats)
        cache.set('home_featured_ids', featured_ids, getattr(settings, 'CACHE_TTL_MANGA', 86400))

    if not latest_ids:
        raw_latest = fetch_latest_manga(limit=24)
        latest_ids = [m['id'] for m in raw_latest]
        for m in raw_latest:
            _save_manga_to_cache(m)
        cache.set('home_latest_ids', latest_ids, getattr(settings, 'CACHE_TTL_MANGA', 86400))

    def _order_qs(ids):
        if not ids: return []
        qs = CachedManga.objects.prefetch_related('genres').filter(mangadex_id__in=ids)
        mangas = {m.mangadex_id: m for m in qs}
        return [mangas[i] for i in ids if i in mangas]

    return {
        'featured': _order_qs(featured_ids),
        'latest': _order_qs(latest_ids),
    }

def search_manga(
    query: str = '',
    genre_include: list[str] | None = None,
    genre_exclude: list[str] | None = None,
    status: str = '',
    manga_type: str = '',
    sort: str = 'latest',
    page: int = 1,
    page_size: int = 24,
) -> tuple[list, int]:
    params: dict = {
        'limit': page_size,
        'offset': (page - 1) * page_size,
        'includes[]': ['cover_art', 'author'],
        'contentRating[]': ['safe', 'suggestive'],
        'availableTranslatedLanguage[]': 'en',
    }
    if query:
        params['title'] = query
    if status:
        params['status[]'] = status
    if manga_type:
        params['originalLanguage[]'] = [manga_type]
    sort_map = {
        'latest': ('latestUploadedChapter', 'desc'),
        'popular': ('followedCount', 'desc'),
        'title': ('title', 'asc'),
        '-title': ('title', 'desc'),
        'year': ('year', 'asc'),
    }
    order_field, order_dir = sort_map.get(sort, ('latestUploadedChapter', 'desc'))
    params[f'order[{order_field}]'] = order_dir
    if genre_include:
        params['includedTags[]'] = genre_include
    if genre_exclude:
        params['excludedTags[]'] = genre_exclude
    data = _api_get('/manga', params=params)
    if not data:
        qs = selectors.search_manga_in_cache(query, genre_include, genre_exclude,
                                              status, manga_type, sort)
        total = qs.count()
        start = (page - 1) * page_size
        return list(qs[start:start + page_size]), total
    results = data.get('data', [])
    total = data.get('total', len(results))
    manga_list = []
    for m in results:
        cached = _save_manga_to_cache(m)
        manga_list.append(cached)
    return manga_list, total
def toggle_bookmark(user, manga: CachedManga, list_type: str = 'reading') -> dict:
    existing = selectors.get_user_bookmark(user, manga)
    if not list_type:
        if existing:
            existing.delete()
        return {'action': 'removed', 'bookmark': None}
    if existing is None:
        bookmark = Bookmark.objects.create(user=user, manga=manga, list_type=list_type)
        return {'action': 'added', 'bookmark': bookmark}
    if existing.list_type != list_type:
        existing.list_type = list_type
        existing.save(update_fields=['list_type', 'updated_at'])
        return {'action': 'updated', 'bookmark': existing}
    return {'action': 'unchanged', 'bookmark': existing}
def record_read(user, chapter: CachedChapter) -> ReadHistory:
    obj, _ = ReadHistory.objects.update_or_create(
        user=user,
        chapter=chapter,
        defaults={'manga': chapter.manga},
    )
    return obj
def seed_genres_from_api() -> int:
    tags = fetch_tags()
    count = 0
    for tag in tags:
        tag_id = tag.get('id', '')
        name_en = tag.get('attributes', {}).get('name', {}).get('en', '')
        if tag_id and name_en:
            Genre.objects.update_or_create(
                mangadex_id=tag_id,
                defaults={'name': name_en, 'slug': slugify(name_en)},
            )
            count += 1
    return count
