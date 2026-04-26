import logging
import time
from typing import Optional
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class MangaDexClient:
    def __init__(self):
        self.base_url = getattr(settings, 'MANGADEX_API_BASE', None)
        self.timeout = getattr(settings, 'MANGADEX_API_TIMEOUT', 25)
        self.headers = {
            'User-Agent': 'Scrollix/1.0 (personal manga reader; contact via github)',
        }

    def api_get(self, path: str, params: dict = None) -> Optional[dict]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout,
            )
            if response.status_code == 429:
                logger.warning("MangaDex rate limit hit — sleeping 2s")
                time.sleep(2)
                response = requests.get(
                    url, 
                    params=params, 
                    headers=self.headers,
                    timeout=self.timeout
                )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("MangaDex API error for %s: %s", path, exc)
            return None

mangadex_client = MangaDexClient()