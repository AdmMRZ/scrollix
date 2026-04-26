from django.db import models
from django.conf import settings
from django.utils import timezone
class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    mangadex_id = models.CharField(max_length=36, unique=True, db_index=True)
    slug = models.SlugField(unique=True)
    class Meta:
        ordering = ['name']
    def __str__(self):
        return self.name
class CachedManga(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('hiatus', 'Hiatus'),
        ('cancelled', 'Cancelled'),
    ]
    mangadex_id = models.CharField(max_length=36, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    alt_titles = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    author = models.CharField(max_length=300, blank=True)
    artist = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True)
    custom_type = models.CharField(max_length=50, blank=True)
    cover_url = models.URLField(max_length=1000, blank=True)
    genres = models.ManyToManyField(Genre, blank=True, related_name='manga')
    year = models.IntegerField(null=True, blank=True)
    content_rating = models.CharField(max_length=30, blank=True)
    last_chapter = models.CharField(max_length=20, blank=True)
    follow_count = models.IntegerField(default=0)
    cached_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-cached_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['cached_at']),
            models.Index(fields=['follow_count']),
        ]
    def __str__(self):
        return self.title
    def is_stale(self, ttl_seconds: int = None) -> bool:
        ttl = ttl_seconds or settings.CACHE_TTL_MANGA
        age = (timezone.now() - self.cached_at).total_seconds()
        return age > ttl
class CachedChapter(models.Model):
    mangadex_id = models.CharField(max_length=36, unique=True, db_index=True)
    manga = models.ForeignKey(
        CachedManga, on_delete=models.CASCADE, related_name='chapters'
    )
    chapter_number = models.CharField(max_length=20, blank=True)
    volume = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=500, blank=True)
    language = models.CharField(max_length=10, default='en')
    pages_count = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    scanlation_group = models.CharField(max_length=300, blank=True)
    cached_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['manga', 'language']),
            models.Index(fields=['published_at']),
        ]
    def __str__(self):
        return f"{self.manga.title} Ch.{self.chapter_number}"
    def is_stale(self, ttl_seconds: int = None) -> bool:
        ttl = ttl_seconds or settings.CACHE_TTL_CHAPTERS
        age = (timezone.now() - self.cached_at).total_seconds()
        return age > ttl
    @property
    def display_number(self):
        return f"Chapter {self.chapter_number}" if self.chapter_number else "Oneshot"
class Bookmark(models.Model):
    LIST_CHOICES = [
        ('reading', 'Reading'),
        ('plan_to_read', 'Plan to Read'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('dropped', 'Dropped'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks'
    )
    manga = models.ForeignKey(
        CachedManga, on_delete=models.CASCADE, related_name='bookmarks'
    )
    list_type = models.CharField(max_length=20, choices=LIST_CHOICES, default='reading')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('user', 'manga')
        ordering = ['-updated_at']
    def __str__(self):
        return f"{self.user.username} → {self.manga.title} [{self.list_type}]"
class ReadHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='read_history'
    )
    chapter = models.ForeignKey(
        CachedChapter, on_delete=models.CASCADE, related_name='read_by'
    )
    manga = models.ForeignKey(
        CachedManga, on_delete=models.CASCADE, related_name='read_history'
    )
    read_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('user', 'chapter')
        ordering = ['-read_at']
    def __str__(self):
        return f"{self.user.username} read {self.chapter}"
