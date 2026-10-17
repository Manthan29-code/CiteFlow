from typing import Any, Dict, List, Optional

import httpx

from citegen.config import settings
from citegen.metadata.models import ArticleMetadata
from citegen.metadata.normalize import normalize_openalex

OPENALEX_API_URL = "https://api.openalex.org/works"


class OpenAlexClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        base_url: str = OPENALEX_API_URL,
    ):
        self.api_key = api_key if api_key is not None else settings.openalex_api_key
        self.timeout = timeout if timeout is not None else settings.request_timeout_seconds
        self.base_url = base_url

    def _get_params(self, title: str, per_page: int) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "search": title,
            "per-page": per_page,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": "CiteGen/0.1.0",
            "Accept": "application/json",
        }
        return headers

    async def search_title(
        self,
        title: str,
        per_page: int = 5,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[ArticleMetadata]:
        """
        Search OpenAlex works by title.
        Returns multiple normalized ArticleMetadata candidates.
        """
        params = self._get_params(title=title, per_page=per_page)
        headers = self._get_headers()

        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            close_client = True

        try:
            resp = await client.get(self.base_url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        finally:
            if close_client:
                await client.aclose()

        results = data.get("results", [])
        candidates: List[ArticleMetadata] = []
        for item in results:
            candidates.append(normalize_openalex(item))
        return candidates


import asyncio

_openalex_semaphore: Optional[asyncio.Semaphore] = None


def get_openalex_semaphore(limit: int = 3) -> asyncio.Semaphore:
    global _openalex_semaphore
    if _openalex_semaphore is None:
        _openalex_semaphore = asyncio.Semaphore(limit)
    return _openalex_semaphore


def set_openalex_semaphore(semaphore: asyncio.Semaphore) -> None:
    global _openalex_semaphore
    _openalex_semaphore = semaphore


async def fetch_openalex_candidates(
    title: str,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
    client: Optional[httpx.AsyncClient] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Dict[str, Any]:
    """
    Failure-isolated wrapper around OpenAlexClient.
    Exceptions NEVER escape this function.
    Returns:
        {"candidates": list[dict], "error": Optional[dict]}
    """
    sem = semaphore or get_openalex_semaphore()
    async with sem:
        c = OpenAlexClient(api_key=api_key, timeout=timeout)
        try:
            candidates = await c.search_title(title=title, client=client)
            return {
                "candidates": [cand.model_dump() for cand in candidates],
                "error": None,
            }
        except httpx.TimeoutException as e:
            return {
                "candidates": [],
                "error": {
                    "provider": "openalex",
                    "type": "timeout",
                    "message": f"OpenAlex request timed out: {e}",
                },
            }
        except httpx.HTTPStatusError as e:
            return {
                "candidates": [],
                "error": {
                    "provider": "openalex",
                    "type": "http_error",
                    "status_code": e.response.status_code,
                    "message": f"OpenAlex HTTP {e.response.status_code}: {e.response.text}",
                },
            }
        except Exception as e:
            return {
                "candidates": [],
                "error": {
                    "provider": "openalex",
                    "type": "general_error",
                    "message": str(e),
                },
            }

