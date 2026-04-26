from django import template
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
    return f'/api/img-proxy/?url={quote(url, safe="")}'

