from typing import Any, Dict, List, Optional

import httpx

from citegen.config import settings
from citegen.metadata.models import ArticleMetadata
from citegen.metadata.normalize import normalize_crossref

CROSSREF_API_URL = "https://api.crossref.org/works"


class CrossrefClient:
    def __init__(
        self,
        mailto: Optional[str] = None,
        timeout: Optional[float] = None,
        base_url: str = CROSSREF_API_URL,
    ):
        self.mailto = mailto if mailto is not None else settings.crossref_mailto
        self.timeout = timeout if timeout is not None else settings.request_timeout_seconds
        self.base_url = base_url

    def _get_headers(self) -> Dict[str, str]:
        user_agent = "CiteGen/0.1.0"
        if self.mailto:
            user_agent = f"{user_agent} (mailto:{self.mailto})"
        return {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

    async def search_title(
        self,
        title: str,
        rows: int = 5,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[ArticleMetadata]:
        """
        Search Crossref by title.
        Returns multiple normalized ArticleMetadata candidates.
        Raises exceptions to be caught by provider wrapper/node.
        """
        params = {
            "query.title": title,
            "rows": rows,
        }
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

        message = data.get("message", {})
        items = message.get("items", [])
        candidates: List[ArticleMetadata] = []
        for item in items:
            candidates.append(normalize_crossref(item))
        return candidates


async def fetch_crossref_candidates(
    title: str,
    mailto: Optional[str] = None,
    timeout: Optional[float] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """
    Failure-isolated wrapper around CrossrefClient.
    Exceptions NEVER escape this function.
    Returns:
        {"candidates": list[dict], "error": Optional[dict]}
    """
    c = CrossrefClient(mailto=mailto, timeout=timeout)
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
                "provider": "crossref",
                "type": "timeout",
                "message": f"Crossref request timed out: {e}",
            },
        }
    except httpx.HTTPStatusError as e:
        return {
            "candidates": [],
            "error": {
                "provider": "crossref",
                "type": "http_error",
                "status_code": e.response.status_code,
                "message": f"Crossref HTTP {e.response.status_code}: {e.response.text}",
            },
        }
    except Exception as e:
        return {
            "candidates": [],
            "error": {
                "provider": "crossref",
                "type": "general_error",
                "message": str(e),
            },
        }
