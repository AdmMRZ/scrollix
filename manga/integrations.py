import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from django.conf import settings

logger = logging.getLogger(__name__)

class MangaDexClient:
    def __init__(self):
        self.base_url = getattr(settings, 'MANGADEX_API_BASE', None)
        self.connect_timeout = getattr(settings, 'MANGADEX_API_CONNECT_TIMEOUT', 3.05)
        self.read_timeout = getattr(settings, 'MANGADEX_API_READ_TIMEOUT', 8.0)
        self.timeout = (self.connect_timeout, self.read_timeout)
        self.headers = {
            'User-Agent': 'Scrollix/1.0 (personal manga reader; contact via github)',
        }
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self.headers)

        retries = Retry(
            total=getattr(settings, 'MANGADEX_API_MAX_RETRIES', 2),
            backoff_factor=getattr(settings, 'MANGADEX_API_BACKOFF_FACTOR', 0.3),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset({'GET'}),
            respect_retry_after_header=True,
        )

        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=getattr(settings, 'MANGADEX_HTTP_POOL_CONNECTIONS', 10),
            pool_maxsize=getattr(settings, 'MANGADEX_HTTP_POOL_MAXSIZE', 20),
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        return session

    def api_get(self, path: str, params: dict = None) -> Optional[dict]:
        if not self.base_url:
            logger.error("MangaDex API base URL is not configured")
            return None

        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("MangaDex API error for %s: %s", path, exc)
            raise

    def stream_image(self, url: str) -> tuple[iter, str]:
        headers = {
            'User-Agent': 'Scrollix/1.0 (personal manga reader; contact via github)',
            'Referer': 'https://mangadex.org/',
        }
        response = self.session.get(
            url,
            headers=headers,
            timeout=15,
            stream=True,
        )
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        return response.iter_content(chunk_size=8192), content_type


mangadex_client = MangaDexClient()