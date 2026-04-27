import math
from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.template.loader import render_to_string
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from . import services, selectors
from .forms import SearchForm
PAGE_SIZE = 24
class HomeView(TemplateView):
    template_name = 'manga/home.html'
    @method_decorator(ratelimit(key='ip', rate='60/m', method='GET', block=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(services.get_homepage_data())
        return ctx
    
class BrowseView(TemplateView):
    template_name = 'manga/browse.html'
    @method_decorator(ratelimit(key='ip', rate='30/m', method='GET', block=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
        
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = SearchForm(self.request.GET or None)
        page = int(self.request.GET.get('page', 1))
        
        search_query = self._build_search_query(form, page)
        manga_list, total = services.search_manga(search_query)
        
        total_pages = math.ceil(total / PAGE_SIZE) if total else 1
        
        ctx.update({
            'form': form,
            'manga_list': manga_list,
            'total': total,
            'page': page,
            'total_pages': total_pages,
            'genres': selectors.get_all_genres(),
            'page_range': range(max(1, page - 2), min(total_pages + 1, page + 3))
        })
        return ctx

    def _build_search_query(self, form: SearchForm, page: int) -> services.MangaSearchQuery:
        """Encapsulate form handling and search query building."""
        if form.is_valid():
            cd = form.cleaned_data
            return services.MangaSearchQuery(
                query=cd.get('q', ''),
                genre_include=cd.get('genres_include', []),
                genre_exclude=cd.get('genres_exclude', []),
                status=cd.get('status', ''),
                manga_type=cd.get('manga_type'),
                sort=cd.get('sort') or 'latest',
                page=page,
                page_size=PAGE_SIZE,
            )
        return services.MangaSearchQuery(sort='latest', page=page, page_size=PAGE_SIZE)
    
class MangaDetailView(TemplateView):
    template_name = 'manga/detail.html'
    @method_decorator(ratelimit(key='ip', rate='60/m', method='GET', block=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
        
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mangadex_id = str(self.kwargs['mangadex_id'])
        manga = services.get_or_fetch_manga(mangadex_id)
        
        if manga is None:
            ctx['not_found'] = True
            return ctx
            
        chapters = services.get_or_fetch_chapters(manga)
        chapters.reverse()
        
        user_bookmark = self._get_user_bookmark(manga)
        truncated_chapters_data = self._truncate_chapters(chapters)
        
        ctx.update({
            'manga': manga,
            'user_bookmark': user_bookmark,
            'bookmark_choices': self._get_bookmark_choices()
        })
        ctx.update(truncated_chapters_data)
        
        return ctx

    def _get_user_bookmark(self, manga):
        if self.request.user.is_authenticated:
            return selectors.get_user_bookmark(self.request.user, manga)
        return None

    def _get_bookmark_choices(self):
        return [
            ('reading', 'Reading'),
            ('plan_to_read', 'Plan to Read'),
            ('completed', 'Completed'),
            ('on_hold', 'On Hold'),
            ('dropped', 'Dropped'),
        ]

    def _truncate_chapters(self, chapters):
        chapter_count = len(chapters)
        THRESHOLD, TOP, BOTTOM = 15, 6, 3
        is_truncated = chapter_count > THRESHOLD
        
        if is_truncated:
            return {
                'chapters_top': chapters[:TOP],
                'chapters_bottom': chapters[chapter_count - BOTTOM:],
                'chapter_count': chapter_count,
                'is_truncated': True,
                'hidden_count': chapter_count - TOP - BOTTOM
            }
            
        return {
            'chapters_top': chapters,
            'chapters_bottom': [],
            'chapter_count': chapter_count,
            'is_truncated': False,
            'hidden_count': 0
        }
    
class ChapterListAllView(View):
    def get(self, request, *args, **kwargs):
        mangadex_id = str(kwargs['mangadex_id'])
        manga = services.get_or_fetch_manga(mangadex_id)
        if manga is None:
            return HttpResponse('', status=404)
        chapters = services.get_or_fetch_chapters(manga)
        chapters.reverse()  
        html = render_to_string('manga/_chapter_list_all.html', {'chapters': chapters}, request=request)
        return HttpResponse(html)

class ReaderView(TemplateView):
    template_name = 'manga/reader.html'
    @method_decorator(ratelimit(key='ip', rate='30/m', method='GET', block=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        chapter_id = str(self.kwargs['chapter_id'])
        reader_data = services.get_reader_data(chapter_id)
        if reader_data is None:
            ctx['not_found'] = True
            return ctx
        if self.request.user.is_authenticated:
            services.record_read(self.request.user, reader_data['chapter'])
        ctx.update(reader_data)
        return ctx
