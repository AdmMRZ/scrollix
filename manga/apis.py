import json
import urllib.parse
import requests as _requests

from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from . import selectors, services

_PROXY_HEADERS = {
    'User-Agent': 'Scrollix/1.0 (personal manga reader; contact via github)',
    'Referer': 'https://mangadex.org/',
}

_ALLOWED_HOSTS = {
    'uploads.mangadex.org',
    'cmdxd98sb0x3yprd.mangadex.network',
    's2.mangadex.org',
}

@method_decorator(ratelimit(key='ip', rate='100/m', method='GET', block=True), name='dispatch')
class ImageProxyView(View):
    def get(self, request, *args, **kwargs):
        raw_url = request.GET.get('url', '').strip()
        if not raw_url:
            return HttpResponse(status=400)

        try:
            parsed = urllib.parse.urlparse(raw_url)
        except Exception:
            return HttpResponse(status=400)

        if parsed.hostname not in _ALLOWED_HOSTS:
            return HttpResponse(status=403)

        try:
            upstream = _requests.get(
                raw_url,
                headers=_PROXY_HEADERS,
                timeout=15,
                stream=True,
            )
            upstream.raise_for_status()
        except _requests.RequestException:
            return HttpResponse(status=502)

        content_type = upstream.headers.get('Content-Type', 'image/jpeg')
        response = StreamingHttpResponse(
            upstream.iter_content(chunk_size=8192),
            content_type=content_type,
        )
        response['Cache-Control'] = 'public, max-age=86400'
        return response


@method_decorator(ratelimit(key='user', rate='30/m', method='POST', block=True), name='dispatch')
class ToggleBookmarkView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        mangadex_id = body.get('mangadex_id', '')
        list_type = body.get('list_type', 'reading')

        manga = selectors.get_manga_by_mangadex_id(mangadex_id)
        if manga is None:
            return JsonResponse({'error': 'Manga not found'}, status=404)

        result = services.toggle_bookmark(request.user, manga, list_type)
        return JsonResponse({
            'action': result['action'],
            'list_type': result['bookmark'].list_type if result['bookmark'] else None,
        })
