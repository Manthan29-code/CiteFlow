import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Union

import httpx

from citegen.config import settings

logger = logging.getLogger(__name__)


async def fetch_grobid_title(
    pdf_path: Union[str, Path],
    grobid_url: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Optional[str]:
    """
    Query GROBID service to extract article title from PDF header.

    Returns the title string if successful, or None if unreachable,
    timed out, or error response. Never crashes on failures.
    """
    base_url = (grobid_url or settings.grobid_url).rstrip("/")
    endpoint = f"{base_url}/api/processHeaderDocument"
    req_timeout = timeout if timeout is not None else settings.request_timeout_seconds
    path = Path(pdf_path)

    if not path.is_file():
        return None

    try:
        with open(path, "rb") as f:
            pdf_bytes = f.read()

        files = {"input": (path.name, pdf_bytes, "application/pdf")}

        async with httpx.AsyncClient(timeout=req_timeout) as client:
            resp = await client.post(endpoint, files=files)

        if resp.status_code != 200:
            logger.warning("GROBID returned status %d: %s", resp.status_code, resp.text[:200])
            return None

        # Parse TEI XML output
        root = ET.fromstring(resp.text)
        # Look for title elements (with or without TEI namespace)
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "title":
                title_text = "".join(elem.itertext()).strip()
                if title_text:
                    normalized = " ".join(title_text.split())
                    return normalized

        return None

    except httpx.RequestError as exc:
        logger.info("GROBID request failed (unreachable or timeout): %s", exc)
        return None
    except ET.ParseError as exc:
        logger.warning("GROBID returned invalid XML: %s", exc)
        return None
    except Exception as exc:
        logger.debug("GROBID query failed (service down or unmocked): %s", exc)
        return None


async def is_grobid_alive(
    grobid_url: Optional[str] = None,
    timeout: float = 3.0,
) -> bool:
    """Check if GROBID service is alive and reachable."""
    base_url = (grobid_url or settings.grobid_url).rstrip("/")
    endpoint = f"{base_url}/api/isalive"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(endpoint)
            return resp.status_code == 200
    except Exception:
        return False
