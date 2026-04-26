import math
from django.views.generic import TemplateView
from django.core.paginator import Paginator
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
        manga_list = []
        total = 0
        page = int(self.request.GET.get('page', 1))
        if form.is_valid():
            cd = form.cleaned_data
            search_query = services.MangaSearchQuery(
                query=cd['q'],
                genre_include=cd['genres_include'],
                genre_exclude=cd['genres_exclude'],
                status=cd['status'],
                manga_type=cd.get('manga_type'),
                sort=cd['sort'] or 'latest',
                page=page,
                page_size=PAGE_SIZE,
            )
            manga_list, total = services.search_manga(search_query)
        else:
            search_query = services.MangaSearchQuery(
                sort='latest', page=page, page_size=PAGE_SIZE
            )
            manga_list, total = services.search_manga(search_query)
        total_pages = math.ceil(total / PAGE_SIZE) if total else 1
        ctx['form'] = form
        ctx['manga_list'] = manga_list
        ctx['total'] = total
        ctx['page'] = page
        ctx['total_pages'] = total_pages
        ctx['genres'] = selectors.get_all_genres()
        ctx['page_range'] = range(max(1, page - 2), min(total_pages + 1, page + 3))
        return ctx
    
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
        is_view_all = self.request.GET.get('all') == '1'
        per_page = max(1, len(chapters)) if is_view_all else 50
        paginator = Paginator(chapters, per_page)
        ch_page = paginator.get_page(self.request.GET.get('ch_page', 1))
        user_bookmark = None
        if self.request.user.is_authenticated:
            user_bookmark = selectors.get_user_bookmark(self.request.user, manga)
        ctx['manga'] = manga
        ctx['chapters_page'] = ch_page
        ctx['chapter_count'] = len(chapters)
        ctx['is_view_all'] = is_view_all
        ctx['user_bookmark'] = user_bookmark
        ctx['bookmark_choices'] = [
            ('reading', 'Reading'),
            ('plan_to_read', 'Plan to Read'),
            ('completed', 'Completed'),
            ('on_hold', 'On Hold'),
            ('dropped', 'Dropped'),
        ]
        return ctx
    
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
