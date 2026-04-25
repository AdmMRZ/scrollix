import json
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from . import selectors, services

class ToggleBookmarkView(LoginRequiredMixin, View):
    """POST endpoint: add/update/remove bookmark. Returns JSON."""

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
