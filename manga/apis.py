import json
import urllib.parse
import requests

from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from . import selectors, services
from .integrations import mangadex_client

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

        if not self._is_valid_host(raw_url):
            return HttpResponse(status=403)

        try:
            stream_content, content_type = mangadex_client.stream_image(raw_url)
        except requests.RequestException:
            return HttpResponse(status=502)

        response = StreamingHttpResponse(stream_content, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=86400'
        return response
        
    def _is_valid_host(self, raw_url: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(raw_url)
            return parsed.hostname in _ALLOWED_HOSTS
        except Exception:
            return False

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
