from __future__ import annotations
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.core.cache import cache
from django.utils.dateparse import parse_datetime
from dataclasses import dataclass, field
from .models import CachedManga, CachedChapter, Genre, Bookmark, ReadHistory
from . import selectors
from .integrations import mangadex_client

@dataclass
class MangaSearchQuery:
    query: str = ''
    genre_include: list[str] = field(default_factory=list)
    genre_exclude: list[str] = field(default_factory=list)
    status: str = ''
    manga_type: str = ''
    sort: str = 'latest'
    page: int = 1
    page_size: int = 24

logger = logging.getLogger(__name__)

def fetch_manga_detail(mangadex_id: str) -> dict | None:
    data = mangadex_client.api_get(f"/manga/{mangadex_id}", params={
        'includes[]': ['author', 'artist', 'cover_art'],
    })
    return data.get('data') if data else None
    
def fetch_manga_list(params: dict) -> list[dict]:
    data = mangadex_client.api_get('/manga', params=params)
    return data.get('data', []) if data else []

def fetch_chapter_feed(mangadex_id: str, language: str = 'en') -> list[dict]:
    chapters = []
    offset = 0
    limit = 500
    while True:
        data = mangadex_client.api_get(f"/manga/{mangadex_id}/feed", params={
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
    data = mangadex_client.api_get(f"/at-home/server/{chapter_id}")
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
    data = mangadex_client.api_get('/manga/tag')
    return data.get('data', []) if data else []

def fetch_popular_manga(limit: int = 20) -> list[dict]:
    return _fetch_manga_by_order('followedCount', limit)

def fetch_latest_manga(limit: int = 24) -> list[dict]:
    return _fetch_manga_by_order('latestUploadedChapter', limit)

def _fetch_manga_by_order(order_key: str, limit: int) -> list[dict]:
    """Helper to fetch manga with default includes and rating."""
    return fetch_manga_list({
        f'order[{order_key}]': 'desc',
        'limit': limit,
        'includes[]': ['cover_art', 'author', 'artist'],
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
    filename = _get_rel_attr(manga_data, 'cover_art', 'fileName')
    if filename:
        return f"https://uploads.mangadex.org/covers/{manga_data.get('id')}/{filename}.256.jpg"
    return ''

def _get_rel_attr(data: dict, rel_type: str, attr_name: str) -> str:
    """Safely extracts an attribute from a relationship list."""
    for rel in data.get('relationships', []):
        if rel.get('type') == rel_type:
            return rel.get('attributes', {}).get(attr_name, '')
    return ''

def _get_rel_id(data: dict, rel_type: str) -> str:
    """Safely extracts an ID from a relationship list."""
    for rel in data.get('relationships', []):
        if rel.get('type') == rel_type:
            return rel.get('id', '')
    return ''

def fetch_manga_statistics(mangadex_ids: list[str]) -> dict:
    if not mangadex_ids:
        return {}
    data = mangadex_client.api_get('/statistics/manga', params={'manga[]': mangadex_ids})
    if not data:
        return {}
    return data.get('statistics', {})

def _extract_manga_title(attrs: dict) -> str:
    titles = attrs.get('title', {})
    title = titles.get('en')
    if not title:
        for alt in attrs.get('altTitles', []):
            if 'en' in alt:
                return alt['en']
    return title or titles.get('ja-ro') or titles.get('ja') or next(iter(titles.values()), 'Unknown')

def _extract_manga_creators(manga_data: dict) -> tuple[str, str]:
    author = _get_rel_attr(manga_data, 'author', 'name') or 'Unknown'
    artist = _get_rel_attr(manga_data, 'artist', 'name') or 'Unknown'
    return author, artist

def _resolve_manga_type(original_language: str) -> str:
    type_map = {'ja': 'Manga', 'ko': 'Manhwa', 'zh': 'Manhua'}
    return next((v for k, v in type_map.items() if k in original_language), 'Manga')

def _extract_alt_titles(attrs: dict, primary_title: str) -> list[str]:
    return [
        val for alt in attrs.get('altTitles', [])
        for k, val in alt.items() if val and val != primary_title
    ]

def _extract_description(attrs: dict) -> str:
    desc = attrs.get('description', {})
    return desc.get('en', '') or next(iter(desc.values()), '')

def _extract_genre_data(attrs: dict) -> list[tuple[str, str]]:
    genres = []
    for tag in attrs.get('tags', []):
        tag_id = tag.get('id', '')
        tag_name = tag.get('attributes', {}).get('name', {}).get('en', '')
        if tag_id and tag_name:
            genres.append((tag_id, tag_name))
    return genres

def _upsert_genres(genre_data: list[tuple[str, str]]) -> list[Genre]:
    if not genre_data:
        return []
    existing = {g.mangadex_id: g for g in Genre.objects.filter(mangadex_id__in=[gid for gid, _ in genre_data])}
    to_create = [
        Genre(mangadex_id=gid, name=name, slug=slugify(name))
        for gid, name in genre_data if gid not in existing
    ]
    if to_create:
        Genre.objects.bulk_create(to_create, ignore_conflicts=True)
        new_genres = Genre.objects.filter(mangadex_id__in=[g.mangadex_id for g in to_create])
        existing.update({g.mangadex_id: g for g in new_genres})
    return [existing[gid] for gid, _ in genre_data if gid in existing]

def _build_manga_instance(manga_data: dict, stats: dict) -> tuple[CachedManga, list[tuple[str, str]]]:
    attrs = manga_data.get('attributes', {})
    mangadex_id = manga_data.get('id', '')
    title = _extract_manga_title(attrs)
    author, artist = _extract_manga_creators(manga_data)
    follow_count = stats.get(mangadex_id, {}).get('follows', 0) if stats else 0

    instance = CachedManga(
        mangadex_id=mangadex_id,
        title=title[:500],
        alt_titles=_extract_alt_titles(attrs, title)[:10],
        description=_extract_description(attrs),
        author=author[:300],
        artist=artist[:300],
        status=attrs.get('status', '')[:20],
        custom_type=_resolve_manga_type(attrs.get('originalLanguage', '')),
        cover_url=_parse_cover_url(manga_data),
        year=attrs.get('year'),
        content_rating=attrs.get('contentRating', '')[:30],
        last_chapter=str(attrs.get('lastChapter') or '')[:20],
        follow_count=follow_count,
    )
    genre_data = _extract_genre_data(attrs)
    return instance, genre_data


def _sync_manga_genres_bulk(
    saved_mangas: dict[str, CachedManga],
    all_genres_data: dict[str, list[tuple[str, str]]],
    genre_objects: dict[str, Genre],
) -> None:
    if not saved_mangas:
        return

    through_model = CachedManga.genres.through
    manga_pks = [m.pk for m in saved_mangas.values() if m.pk]
    if not manga_pks:
        return

    desired_relations: set[tuple[int, int]] = set()
    for manga_id, genre_data in all_genres_data.items():
        manga = saved_mangas.get(manga_id)
        if not manga or not manga.pk:
            continue
        for genre_id, _ in genre_data:
            genre = genre_objects.get(genre_id)
            if genre and genre.pk:
                desired_relations.add((manga.pk, genre.pk))

    with transaction.atomic():
        through_model.objects.filter(cachedmanga_id__in=manga_pks).delete()
        if desired_relations:
            through_model.objects.bulk_create(
                [
                    through_model(cachedmanga_id=manga_pk, genre_id=genre_pk)
                    for manga_pk, genre_pk in desired_relations
                ],
                ignore_conflicts=True,
            )

def _save_mangas_to_cache(manga_data_list: list[dict], stats: dict = None) -> list[CachedManga]:
    if not manga_data_list:
        return []

    all_genres_data: dict[str, list[tuple[str, str]]] = {}
    instances = []
    for manga_data in manga_data_list:
        instance, genre_data = _build_manga_instance(manga_data, stats or {})
        if instance.mangadex_id:
            instances.append(instance)
            all_genres_data[instance.mangadex_id] = genre_data

    if not instances:
        return []

    update_fields = [
        'title', 'alt_titles', 'description', 'author', 'artist',
        'status', 'custom_type', 'cover_url', 'year', 'content_rating',
        'last_chapter', 'follow_count',
    ]
    CachedManga.objects.bulk_create(
        instances,
        update_conflicts=True,
        unique_fields=['mangadex_id'],
        update_fields=update_fields,
    )

    manga_ids = [i.mangadex_id for i in instances]
    saved_mangas = {
        m.mangadex_id: m
        for m in CachedManga.objects.filter(mangadex_id__in=manga_ids)
    }

    all_genre_pairs = list({gid: name for gd in all_genres_data.values() for gid, name in gd}.items())
    genre_objects = {g.mangadex_id: g for g in _upsert_genres(all_genre_pairs)}

    _sync_manga_genres_bulk(saved_mangas, all_genres_data, genre_objects)

    return [saved_mangas[i.mangadex_id] for i in instances if i.mangadex_id in saved_mangas]

def _save_manga_to_cache(manga_data: dict, stats: dict = None) -> CachedManga:
    results = _save_mangas_to_cache([manga_data], stats=stats)
    return results[0] if results else None

def _get_mangas_by_ids(ids: list[str]) -> list[CachedManga]:
    if not ids:
        return []
    qs = CachedManga.objects.prefetch_related('genres').filter(mangadex_id__in=ids)
    mangas = {m.mangadex_id: m for m in qs}
    return [mangas[i] for i in ids if i in mangas]
def _extract_scanlation_group(relationships: list[dict]) -> str:
    for rel in relationships:
        if rel.get('type') == 'scanlation_group':
            return rel.get('attributes', {}).get('name', '') or ''
    return ''

def _parse_chapter_published_date(attrs: dict):
    published_str = attrs.get('publishAt') or attrs.get('createdAt')
    if published_str:
        return parse_datetime(published_str)
    return None

def _build_chapter_instance(manga: CachedManga, chapter_data: dict) -> CachedChapter | None:
    chapter_id = chapter_data.get('id', '')
    if not chapter_id:
        return None

    attrs = chapter_data.get('attributes', {})
    scanlation = _extract_scanlation_group(chapter_data.get('relationships', []))
    published_at = _parse_chapter_published_date(attrs)

    return CachedChapter(
        mangadex_id=chapter_id,
        manga=manga,
        chapter_number=str(attrs.get('chapter') or '')[:20],
        volume=str(attrs.get('volume') or '')[:20],
        title=str(attrs.get('title') or '')[:500],
        language=attrs.get('translatedLanguage', 'en')[:10],
        pages_count=attrs.get('pages', 0),
        published_at=published_at,
        scanlation_group=scanlation[:300],
        cached_at=timezone.now(),
    )

def _save_chapters_to_cache(manga: CachedManga, chapters_data: list[dict]) -> None:
    chapters_to_upsert = []
    
    for ch_data in chapters_data:
        chapter = _build_chapter_instance(manga, ch_data)
        if chapter:
            chapters_to_upsert.append(chapter)

    if chapters_to_upsert:
        CachedChapter.objects.bulk_create(
            chapters_to_upsert,
            update_conflicts=True,
            unique_fields=['mangadex_id'],
            update_fields=[
                'chapter_number', 'volume', 'title', 'language', 
                'pages_count', 'published_at', 'scanlation_group', 'cached_at'
            ]
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

    featured_manga = []
    latest_manga = []

    if featured_ids and latest_ids:
        all_ids = featured_ids + latest_ids
        all_mangas = _get_mangas_by_ids(all_ids)
        manga_map = {m.mangadex_id: m for m in all_mangas}
        
        return {
            'featured': [manga_map[i] for i in featured_ids if i in manga_map],
            'latest': [manga_map[i] for i in latest_ids if i in manga_map],
        }

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_featured = None
        future_latest = None

        if not featured_ids:
            future_featured = executor.submit(_refresh_featured_manga)
        if not latest_ids:
            future_latest = executor.submit(_refresh_latest_manga)

        featured_manga = future_featured.result() if future_featured else _get_mangas_by_ids(featured_ids)
        latest_manga = future_latest.result() if future_latest else _get_mangas_by_ids(latest_ids)

    return {
        'featured': featured_manga,
        'latest': latest_manga,
    }

def _refresh_featured_manga() -> list[CachedManga]:
    raw_popular = fetch_popular_manga(limit=6)
    featured_ids = [m['id'] for m in raw_popular]
    
    stats = fetch_manga_statistics(featured_ids)
    mangas = _save_mangas_to_cache(raw_popular, stats=stats)
    
    ttl = getattr(settings, 'CACHE_TTL_MANGA', 86400)
    cache.set('home_featured_ids', featured_ids, ttl)
    return mangas

def _refresh_latest_manga() -> list[CachedManga]:
    raw_latest = fetch_latest_manga(limit=25)
    latest_ids = [m['id'] for m in raw_latest]
    
    mangas = _save_mangas_to_cache(raw_latest)
    
    ttl = getattr(settings, 'CACHE_TTL_MANGA', 86400)
    cache.set('home_latest_ids', latest_ids, ttl)
    cache.set('home_latest_total', 10000, ttl)
    return mangas

def _search_cache_key(search_query: MangaSearchQuery) -> str:
    parts = [
        f"q={search_query.query}",
        f"sort={search_query.sort}",
        f"page={search_query.page}",
        f"size={search_query.page_size}",
        f"status={search_query.status}",
        f"type={search_query.manga_type}",
        f"inc={','.join(sorted(search_query.genre_include))}",
        f"exc={','.join(sorted(search_query.genre_exclude))}",
    ]
    return "search:" + "|".join(parts)

def _build_search_params(search_query: MangaSearchQuery) -> dict:
    """Builds the API request parameters from a MangaSearchQuery object."""
    params: dict = {
        'limit': search_query.page_size,
        'offset': (search_query.page - 1) * search_query.page_size,
        'includes[]': ['cover_art', 'author'],
        'contentRating[]': ['safe', 'suggestive'],
        'availableTranslatedLanguage[]': 'en',
    }
    if search_query.query:
        params['title'] = search_query.query
    if search_query.status:
        params['status[]'] = search_query.status
    if search_query.manga_type:
        params['originalLanguage[]'] = [search_query.manga_type]
    
    sort_map = {
        'latest': ('latestUploadedChapter', 'desc'),
        'popular': ('followedCount', 'desc'),
        'title': ('title', 'asc'),
        '-title': ('title', 'desc'),
        'year': ('year', 'asc'),
    }
    order_field, order_dir = sort_map.get(search_query.sort, ('latestUploadedChapter', 'desc'))
    params[f'order[{order_field}]'] = order_dir
    
    if search_query.genre_include:
        params['includedTags[]'] = search_query.genre_include
    if search_query.genre_exclude:
        params['excludedTags[]'] = search_query.genre_exclude
        
    return params

def _is_default_latest(sq: MangaSearchQuery) -> bool:
    return (
        not sq.query
        and not sq.status
        and not sq.manga_type
        and not sq.genre_include
        and not sq.genre_exclude
        and sq.sort in ('latest', '')
        and sq.page == 1
    )

def search_manga(
    search_query: MangaSearchQuery,
) -> tuple[list, int]:
    ttl = getattr(settings, 'CACHE_TTL_MANGA', 86400)

    if _is_default_latest(search_query):
        ids = cache.get('home_latest_ids')
        if ids:
            ids = ids[:search_query.page_size]
            manga_list = _get_mangas_by_ids(ids)
            total = cache.get('home_latest_total', len(manga_list))
            return manga_list, total

    cache_key = _search_cache_key(search_query)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        ids, total = cached_payload
        return _get_mangas_by_ids(ids), total

    params = _build_search_params(search_query)

    data = mangadex_client.api_get('/manga', params=params)
    if not data:
        qs = selectors.search_manga_in_cache(
            search_query.query, search_query.genre_include, search_query.genre_exclude,
            search_query.status, search_query.manga_type, search_query.sort,
        )
        total = qs.count()
        start = (search_query.page - 1) * search_query.page_size
        return list(qs[start:start + search_query.page_size]), total

    results = data.get('data', [])
    total = data.get('total', len(results))

    manga_list = _save_mangas_to_cache(results)
    ids = [m.mangadex_id for m in manga_list]

    cache.set(cache_key, (ids, total), ttl)

    if _is_default_latest(search_query):
        cache.set('home_latest_ids', ids, ttl)
        cache.set('home_latest_total', total, ttl)

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
        manga=chapter.manga,
        defaults={'chapter': chapter},
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
