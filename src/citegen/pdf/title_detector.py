import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pymupdf

from citegen.config import settings
from citegen.pdf.grobid_client import fetch_grobid_title

logger = logging.getLogger(__name__)

# Excluded keywords for titles
JOURNAL_KEYWORDS = [
    "journal of",
    "physical review",
    "proceedings of",
    "transactions on",
    "letters to",
    "annual review",
    "bulletin of",
    "nature",
    "science",
    "ieee",
    "springer",
    "elsevier",
    "wiley",
    "oxford university press",
    "applied physics",
    "plasma sources",
]

AFFILIATION_KEYWORDS = [
    "department of",
    "faculty of",
    "university",
    "institute of",
    "laboratory",
    "school of",
    "center for",
    "college",
    "division of",
    "@ ",
    "@",
    "email:",
    "correspondence:",
    "e-mail",
]

HEADER_FOOTER_PATTERNS = [
    re.compile(r"page\s+\d+(\s+of\s+\d+)?", re.IGNORECASE),
    re.compile(r"doi:\s*10\.\d+", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"issn\s*\d+", re.IGNORECASE),
    re.compile(r"vol(ume)?\.?\s*\d+", re.IGNORECASE),
    re.compile(r"©|copyright|\ball\s+rights\s+reserved\b", re.IGNORECASE),
    re.compile(r"received\s+\d+.*accepted\s+\d+", re.IGNORECASE),
]

SECTION_PATTERNS = [
    re.compile(r"^(abstract|introduction|references|contents|index)\b", re.IGNORECASE),
]


def _is_header_or_footer(
    text: str, y0: float, y1: float, page_height: float, font_size: float, body_size: float
) -> bool:
    """Check if a text span or block is likely a header or footer."""
    # Strict margins
    if y0 < 38 or y1 > (page_height - 38):
        return True

    # Font size is at or below body font and matches header patterns
    text_lower = text.lower()
    for pattern in HEADER_FOOTER_PATTERNS:
        if pattern.search(text_lower):
            return True

    return False


def _is_journal_or_publisher(text: str) -> bool:
    """Check if text is likely a journal title or publisher line."""
    lower = text.lower()
    return any(kw in lower for kw in JOURNAL_KEYWORDS)


def _is_author_or_affiliation(text: str) -> bool:
    """Check if text is an author name list or institutional affiliation."""
    lower = text.lower()
    # Check affiliation words
    if any(kw in lower for kw in AFFILIATION_KEYWORDS):
        return True

    # Check author-list pattern (e.g., "A. Author, B. Author and C. Author")
    if (
        re.search(r"\b(and|et al\.)\b", lower)
        and len(text.split()) < 10
        and not any(p in lower for p in ["theory", "study", "analysis", "instabilities", "plasma"])
    ):
        if re.search(r"[A-Z]\.\s*[A-Z]?[a-z]*", text):
            return True

    return False


def extract_title_candidates_from_doc(
    doc: pymupdf.Document, max_pages: int = 5
) -> List[Dict[str, Any]]:
    """
    Extract title candidates across early pages using font size and positional heuristics.
    """
    num_pages = min(doc.page_count, max_pages)

    all_blocks_info: List[Dict[str, Any]] = []

    for page_idx in range(num_pages):
        page = doc.load_page(page_idx)
        page_height = page.rect.height
        page_dict = page.get_text("dict")

        # First pass to find median/body font size on this page
        font_sizes: List[float] = []
        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # text
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if len(span.get("text", "").strip()) > 3:
                            font_sizes.append(span.get("size", 10.0))

        body_font_size = 10.0
        if font_sizes:
            if max(font_sizes) == min(font_sizes) and max(font_sizes) >= 14.0:
                body_font_size = 10.0
            elif len(font_sizes) <= 3:
                body_font_size = min(font_sizes)
            else:
                font_sizes.sort()
                body_font_size = font_sizes[len(font_sizes) // 4]

        # Second pass: group lines into cohesive blocks
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue

            block_lines = block.get("lines", [])
            if not block_lines:
                continue

            # Check spans in lines
            merged_lines: List[str] = []
            block_font_sizes: List[float] = []
            min_y0 = float("inf")
            max_y1 = float("-inf")

            for line in block_lines:
                line_spans = line.get("spans", [])
                line_text = "".join(s.get("text", "") for s in line_spans).strip()
                if not line_text:
                    continue

                for s in line_spans:
                    block_font_sizes.append(s.get("size", 10.0))
                    bbox = s.get("bbox", (0, 0, 0, 0))
                    min_y0 = min(min_y0, bbox[1])
                    max_y1 = max(max_y1, bbox[3])

                merged_lines.append(line_text)

            if not merged_lines or not block_font_sizes:
                continue

            full_block_text = " ".join(" ".join(merged_lines).split())
            avg_font = sum(block_font_sizes) / len(block_font_sizes)

            all_blocks_info.append(
                {
                    "page": page_idx + 1,
                    "text": full_block_text,
                    "avg_font": avg_font,
                    "max_font": max(block_font_sizes),
                    "body_font": body_font_size,
                    "y0": min_y0,
                    "y1": max_y1,
                    "page_height": page_height,
                }
            )

    if not all_blocks_info:
        return []

    # Filter and score candidates
    scored_candidates: List[Tuple[float, Dict[str, Any]]] = []

    for item in all_blocks_info:
        text = item["text"]
        avg_font = item["avg_font"]
        max_font = item["max_font"]
        body_font = item["body_font"]
        y0 = item["y0"]
        y1 = item["y1"]
        page_height = item["page_height"]
        page_num = item["page"]

        # Basic exclusions
        if len(text) < 10 or len(text) > 400:
            continue

        if _is_header_or_footer(text, y0, y1, page_height, avg_font, body_font):
            continue

        if _is_journal_or_publisher(text):
            continue

        if _is_author_or_affiliation(text):
            continue

        for sp in SECTION_PATTERNS:
            if sp.match(text):
                continue

        # Score calculation
        score = 0.0

        # Font ratio bonus
        font_ratio = max_font / max(body_font, 6.0)
        if font_ratio >= 1.5:
            score += 0.55
        elif font_ratio >= 1.25:
            score += 0.40
        elif font_ratio >= 1.05:
            score += 0.20
        else:
            score += 0.05

        # Absolute font size bonus
        if max_font >= 20.0:
            score += 0.35
        elif max_font >= 16.0:
            score += 0.25
        elif max_font >= 13.0:
            score += 0.15

        # Position bonus (upper half of page)
        if y0 < (page_height * 0.45):
            score += 0.15
        elif y0 < (page_height * 0.65):
            score += 0.05

        # Word count bonus (typical titles are 2 to 35 words)
        words = text.split()
        if 2 <= len(words) <= 35:
            score += 0.15
        elif len(words) < 2:
            score -= 0.25

        # Punctuation check: titles rarely end with period
        if text.endswith(".") and not text.endswith("..."):
            score -= 0.10

        # Cap confidence between 0.10 and 0.98
        confidence = max(0.10, min(0.98, score))

        scored_candidates.append(
            (
                confidence,
                {
                    "title": text,
                    "confidence": round(confidence, 2),
                    "source": "pymupdf_heuristics",
                    "reason": (
                        f"Font size {max_font:.1f}pt (ratio {font_ratio:.2f}x) on page {page_num}"
                    ),
                    "page": page_num,
                    "font_size": round(max_font, 1),
                },
            )
        )

    # Sort descending by confidence
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate while preserving order
    seen_titles = set()
    result: List[Dict[str, Any]] = []
    for conf, cand in scored_candidates:
        norm_title = " ".join(cand["title"].lower().split())
        if norm_title not in seen_titles:
            seen_titles.add(norm_title)
            result.append(cand)

    return result


async def detect_title_candidates(
    pdf_path: Union[str, Path],
    grobid_url: Optional[str] = None,
    use_grobid: bool = True,
    fallback_text: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Detect title candidates for a PDF.

    1. Tries GROBID first if configured and reachable.
    2. Runs PyMuPDF font-size and layout heuristics across early pages.
    3. Falls back to text parsing if PyMuPDF returns no blocks (e.g. OCR text).
    Returns ranked list of candidates with confidence scores.
    """
    path = Path(pdf_path)
    candidates: List[Dict[str, Any]] = []

    # 1. Try GROBID if enabled
    if use_grobid and settings.grobid_url:
        grobid_title = await fetch_grobid_title(path, grobid_url=grobid_url)
        if grobid_title:
            candidates.append(
                {
                    "title": grobid_title,
                    "confidence": 0.95,
                    "source": "grobid",
                    "reason": "Extracted via GROBID header analysis",
                    "page": 1,
                    "font_size": None,
                }
            )

    # 2. PyMuPDF layout heuristics
    if path.is_file():
        try:
            doc = pymupdf.open(path)
            try:
                heur_cands = extract_title_candidates_from_doc(doc)
                for cand in heur_cands:
                    # Avoid adding identical title if already from GROBID
                    if not any(cand["title"].lower() == c["title"].lower() for c in candidates):
                        candidates.append(cand)
            finally:
                doc.close()
        except Exception as exc:
            logger.debug("PyMuPDF candidate extraction failed: %s", exc)

    # 3. Fallback to raw text if no candidates found so far
    if not candidates and fallback_text:
        lines = [line.strip() for line in fallback_text.splitlines() if line.strip()]
        for line in lines[:10]:
            if len(line) >= 12 and not _is_header_or_footer(line, 50, 60, 792, 12, 10):
                if not _is_journal_or_publisher(line) and not _is_author_or_affiliation(line):
                    candidates.append(
                        {
                            "title": line,
                            "confidence": 0.50,
                            "source": "ocr_text_fallback",
                            "reason": "First plausible text line from extracted text",
                            "page": 1,
                            "font_size": None,
                        }
                    )
                    break

    # Re-sort descending by confidence
    candidates.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
    return candidates
