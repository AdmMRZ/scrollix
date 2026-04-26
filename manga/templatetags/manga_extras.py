from django import template
from django.conf import settings
from urllib.parse import quote
register = template.Library()


@register.filter
def dict_get(d, key):
    if isinstance(d, dict):
        return d.get(key, 0)
    return 0


@register.filter
def img_proxy(url):
    if not url:
        return ''
    if not getattr(settings, 'USE_IMAGE_PROXY', False):
        return url
    return f'/api/img-proxy/?url={quote(url, safe="")}'

