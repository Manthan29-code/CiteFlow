import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pymupdf

from citegen.config import settings
from citegen.pdf.grobid_client import fetch_grobid_title

logger = logging.getLogger(__name__)

# Excluded keywords for titles.
# Journal names that commonly *start* a running header / journal banner line.
JOURNAL_PREFIX_RE = re.compile(
    r"^(journal\s+of|physical\s+review|proceedings\s+of|transactions\s+on|ieee\s+transactions"
    r"|annual\s+review|bulletin\s+of|letters\s+to|annals\s+of|physics\s+of\s+plasmas"
    r"|applied\s+physics\s+letters|plasma\s+sources\s+science)\b",
    re.IGNORECASE,
)

# Generic journal words: only treated as a journal banner when the block is short.
# (Matching these anywhere would reject real titles such as
#  "High temperature electrons exhausted from rf plasma sources ...".)
SHORT_JOURNAL_RE = re.compile(
    r"\b(nature|science|ieee|applied\s+physics|plasma\s+sources|physics\s+of\s+plasmas)\b",
    re.IGNORECASE,
)
SHORT_JOURNAL_MAX_WORDS = 6

# Publisher names: never part of a real article title.
PUBLISHER_RE = re.compile(
    r"\b(springer|elsevier|wiley|oxford\s+university\s+press|aip\s+publishing|iop\s+publishing"
    r"|american\s+physical\s+society|taylor\s*&\s*francis|cambridge\s+university\s+press)\b",
    re.IGNORECASE,
)

# Affiliation markers that are strong enough on their own.
STRONG_AFFILIATION_KEYWORDS = [
    "department of",
    "faculty of",
    "division of",
    "@",
    "email:",
    "correspondence:",
    "e-mail",
]

# Affiliation markers that can legitimately appear in titles (e.g. "Laboratory
# measurements of ..."); only treated as affiliation if the block also looks like an
# address (contains a comma or a digit).
WEAK_AFFILIATION_KEYWORDS = [
    "university",
    "institute of",
    "laboratory",
    "school of",
    "center for",
    "centre for",
    "college",
]

HEADER_FOOTER_PATTERNS = [
    re.compile(r"page\s+\d+(\s+of\s+\d+)?", re.IGNORECASE),
    re.compile(r"doi:\s*10\.\d+", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"issn\s*\d+", re.IGNORECASE),
    re.compile(r"vol(ume)?\.?\s*\d+", re.IGNORECASE),
    re.compile(r"©|copyright|\ball\s+rights\s+reserved\b", re.IGNORECASE),
    re.compile(r"received\s+\d+.*accepted\s+\d+", re.IGNORECASE),
    # Citation lines such as "Phys. Plasmas 24, 084503 (2017)"
    re.compile(r"\b\d+\s*,\s*[a-z]?\d+\s*\(\d{4}\)", re.IGNORECASE),
]

SECTION_PATTERNS = [
    re.compile(r"^(abstract|introduction|references|contents|index)\b", re.IGNORECASE),
]

# Publisher cover-page / landing-page UI boilerplate (AIP, IOP, APS, Springer, ...).
BOILERPLATE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(view\s+online|export\s+citation|view\s+online\s+export\s+citation)$",
        r"^(cite\s+this\s+(article|paper)|to\s+cite\s+this\s+article)\b",
        r"^check\s+for\s+updates$",
        r"^download(\s+(pdf|article|citation))?$",
        r"^(research|review|original|brief|short)\s+(article|report|paper|communication)\b",
        r"^(accepted\s+manuscript|author\s+accepted\s+manuscript|open\s+access)$",
        r"^(paper|letter|review|article)\s*[•|·-]\s*open\s+access$",
        r"^view\s+the\s+article\s+online\b",
        r"^submit\s+your\s+(article|manuscript)",
        r"^this\s+content\s+was\s+downloaded",
        r"^published\s+(online|by)\b",
        r"^(citation|keywords?)\s*:",
    ]
]

# Headings that introduce a list of *other* papers on a cover page. Everything below
# such a heading on the same page is ignored.
RELATED_SECTION_RE = re.compile(
    r"^(articles?\s+you\s+may\s+be\s+interested\s+in|related\s+articles|you\s+may\s+also\s+like"
    r"|recent\s+citations|related\s+content|more\s+from\s+this\s+journal)\b",
    re.IGNORECASE,
)

# Private Use Area code points are used by icon fonts (e.g. the "View Online" button
# glyphs on AIP cover pages). They carry no text and must not influence font sizes.
PUA_RE = re.compile("[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]")
LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "st",
    "\ufb06": "st",
}
_LIGATURE_TABLE = str.maketrans(LIGATURES)

# Metadata titles that are clearly not article titles.
BAD_METADATA_TITLE_RE = re.compile(
    r"(\.(pdf|docx?|tex|dvi|ps|rtf|indd)$|^microsoft\s+word|^untitled|^title$|^document\d*$"
    r"|^slide\s*\d*$|^\s*$)",
    re.IGNORECASE,
)
METADATA_MATCH_THRESHOLD = 0.90
METADATA_MATCH_BONUS = 0.25
METADATA_ONLY_CONFIDENCE = 0.60
REPEATED_TITLE_BONUS = 0.10
LOW_QUALITY_PENALTY = 0.40
PAGE_PENALTY = 0.02

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _clean_text(text: str) -> str:
    """Normalize ligatures and strip icon-font (Private Use Area) glyphs."""
    return PUA_RE.sub("", text.translate(_LIGATURE_TABLE))


def _normalize_for_compare(text: str) -> str:
    """Lowercase alphanumeric-only form used for fuzzy comparisons."""
    return " ".join(re.sub(r"[^0-9a-z]+", " ", _clean_text(text).lower()).split())


def _similarity(a: str, b: str) -> float:
    na, nb = _normalize_for_compare(a), _normalize_for_compare(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _is_low_quality_text(text: str) -> bool:
    """Detect equations / garbled glyph runs that are not natural-language titles."""
    if CONTROL_CHARS_RE.search(text):
        return True
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return True
    letter_ratio = sum(c.isalpha() for c in chars) / len(chars)
    real_words = len(re.findall(r"[^\W\d_]{3,}", text))
    return letter_ratio < 0.6 or real_words < 2


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
    stripped = text.strip()
    if JOURNAL_PREFIX_RE.match(stripped):
        return True
    if PUBLISHER_RE.search(stripped):
        return True
    if len(stripped.split()) <= SHORT_JOURNAL_MAX_WORDS and SHORT_JOURNAL_RE.search(stripped):
        return True
    return False


def _is_boilerplate(text: str) -> bool:
    """Check if text is publisher cover-page / UI boilerplate."""
    stripped = text.strip()
    if RELATED_SECTION_RE.match(stripped):
        return True
    return any(p.search(stripped) for p in BOILERPLATE_PATTERNS)


def _is_section_heading(text: str) -> bool:
    return any(sp.match(text) for sp in SECTION_PATTERNS)


def _is_author_or_affiliation(text: str) -> bool:
    """Check if text is an author name list or institutional affiliation."""
    lower = text.lower()
    # Check affiliation words
    if any(kw in lower for kw in STRONG_AFFILIATION_KEYWORDS):
        return True
    if any(kw in lower for kw in WEAK_AFFILIATION_KEYWORDS) and re.search(r"[,\d]", text):
        return True

    # Check author-list pattern (e.g., "A. Author, B. Author and C. Author")
    if (
        re.search(r"\b(and|et al\.)\b", lower)
        and len(text.split()) < 10
        and not any(p in lower for p in ["theory", "study", "analysis", "instabilities", "plasma"])
    ):
        if re.search(r"[A-Z]\.\s*[A-Z]?[a-z]*", text):
            return True

    # Initial-heavy name lists separated by ';' or ',' (e.g. "S. K. Saha; S. Chowdhury; ...")
    initials = len(re.findall(r"\b[A-Z]\.(?=\s|-|[A-Z])", text))
    separators = len(re.findall(r"[;,]", text))
    if initials >= 2 and separators >= 1 and initials >= len(text.split()) * 0.3:
        return True

    return False


def _clean_metadata_title(raw: Optional[str]) -> Optional[str]:
    """Return the PDF /Title metadata if it plausibly is an article title."""
    if not raw:
        return None
    title = " ".join(_clean_text(raw).split())
    if len(title) < 10 or len(title.split()) < 3:
        return None
    if BAD_METADATA_TITLE_RE.search(title):
        return None
    if _is_journal_or_publisher(title) or _is_boilerplate(title):
        return None
    return title


def extract_title_candidates_from_doc(
    doc: pymupdf.Document, max_pages: int = 5
) -> List[Dict[str, Any]]:
    """
    Extract title candidates across early pages using font size and positional heuristics.

    Publisher cover pages (AIP/IOP style) are handled by ignoring icon-font glyphs,
    UI boilerplate and "related articles" lists. The PDF /Title metadata and repetition of
    the same large-font text across pages are used as corroborating signals.
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
                        if len(_clean_text(span.get("text", "")).strip()) > 3:
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
        page_blocks: List[Dict[str, Any]] = []
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
                line_text = "".join(_clean_text(s.get("text", "")) for s in line_spans).strip()
                if not line_text:
                    continue

                for s in line_spans:
                    # Icon-only / whitespace-only spans must not inflate font sizes
                    if not _clean_text(s.get("text", "")).strip():
                        continue
                    block_font_sizes.append(s.get("size", 10.0))
                    bbox = s.get("bbox", (0, 0, 0, 0))
                    min_y0 = min(min_y0, bbox[1])
                    max_y1 = max(max_y1, bbox[3])

                merged_lines.append(line_text)

            if not merged_lines or not block_font_sizes:
                continue

            full_block_text = " ".join(" ".join(merged_lines).split())
            avg_font = sum(block_font_sizes) / len(block_font_sizes)

            page_blocks.append(
                {
                    "page": page_idx + 1,
                    "text": full_block_text,
                    "avg_font": avg_font,
                    "max_font": max(block_font_sizes),
                    "body_font": body_font_size,
                    "y0": min_y0,
                    "y1": max_y1,
                    "x0": block.get("bbox", (0, 0, 0, 0))[0],
                    "page_height": page_height,
                }
            )

        # Drop "Articles you may be interested in"-style lists of other papers. The list
        # may sit in a side column (IOP "You may also like"), so only drop blocks below
        # the heading that also start in the heading's column.
        for heading in [b for b in page_blocks if RELATED_SECTION_RE.match(b["text"])]:
            col_x0 = heading["x0"] - 20
            page_blocks = [
                b
                for b in page_blocks
                if b is heading or not (b["y0"] >= heading["y0"] and b["x0"] >= col_x0)
            ]

        all_blocks_info.extend(page_blocks)

    if not all_blocks_info:
        return []

    # Count on how many pages each (prominent) text appears, e.g. cover page + article page
    pages_by_text: Dict[str, set] = {}
    for item in all_blocks_info:
        key = _normalize_for_compare(item["text"])
        if key:
            pages_by_text.setdefault(key, set()).add(item["page"])

    metadata_title = _clean_metadata_title((doc.metadata or {}).get("title"))

    # Filter and score candidates
    scored_candidates: List[Tuple[float, float, Dict[str, Any]]] = []

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

        if _is_boilerplate(text):
            continue

        if _is_journal_or_publisher(text):
            continue

        if _is_author_or_affiliation(text):
            continue

        if _is_section_heading(text):
            continue

        # Score calculation
        score = 0.0
        reasons: List[str] = []

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

        # Equations and garbled glyph runs (large math fonts) are not titles
        if _is_low_quality_text(text):
            score -= LOW_QUALITY_PENALTY

        # Titles appear early in the document; mild preference for earlier pages
        score -= PAGE_PENALTY * (page_num - 1)

        # Same prominent text repeated on several pages (cover page + first article page)
        key = _normalize_for_compare(text)
        if font_ratio >= 1.2 and len(pages_by_text.get(key, ())) >= 2:
            score += REPEATED_TITLE_BONUS
            reasons.append("repeated on multiple pages")

        # Agreement with the PDF /Title metadata
        if metadata_title and _similarity(text, metadata_title) >= METADATA_MATCH_THRESHOLD:
            score += METADATA_MATCH_BONUS
            reasons.append("matches PDF metadata title")

        # Cap confidence between 0.10 and 0.98
        confidence = max(0.10, min(0.98, score))

        reason = f"Font size {max_font:.1f}pt (ratio {font_ratio:.2f}x) on page {page_num}"
        if reasons:
            reason += "; " + "; ".join(reasons)

        scored_candidates.append(
            (
                score,
                font_ratio,
                {
                    "title": text,
                    "confidence": round(confidence, 2),
                    "source": "pymupdf_heuristics",
                    "reason": reason,
                    "page": page_num,
                    "font_size": round(max_font, 1),
                },
            )
        )

    # If no layout candidate agrees with the metadata title, offer it as its own candidate
    if metadata_title and not any(
        _similarity(c[2]["title"], metadata_title) >= METADATA_MATCH_THRESHOLD
        for c in scored_candidates
    ):
        scored_candidates.append(
            (
                METADATA_ONLY_CONFIDENCE,
                0.0,
                {
                    "title": metadata_title,
                    "confidence": METADATA_ONLY_CONFIDENCE,
                    "source": "pdf_metadata",
                    "reason": "Title from PDF document metadata",
                    "page": None,
                    "font_size": None,
                },
            )
        )

    # Sort descending by raw (uncapped) score, then font ratio as a tie-breaker
    scored_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # Deduplicate while preserving order
    seen_titles = set()
    result: List[Dict[str, Any]] = []
    for _score, _ratio, cand in scored_candidates:
        norm_title = _normalize_for_compare(cand["title"])
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
                    if not any(
                        _normalize_for_compare(cand["title"]) == _normalize_for_compare(c["title"])
                        for c in candidates
                    ):
                        candidates.append(cand)
            finally:
                doc.close()
        except Exception as exc:
            logger.debug("PyMuPDF candidate extraction failed: %s", exc)

    # 3. Fallback to raw text if no candidates found so far
    if not candidates and fallback_text:
        lines = [line.strip() for line in fallback_text.splitlines() if line.strip()]
        for line in lines[:10]:
            line = " ".join(_clean_text(line).split())
            if len(line) >= 12 and not _is_header_or_footer(line, 50, 60, 792, 12, 10):
                if (
                    not _is_journal_or_publisher(line)
                    and not _is_author_or_affiliation(line)
                    and not _is_boilerplate(line)
                ):
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

    # Re-sort descending by confidence (stable: preserves heuristic tie-break order)
    candidates.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
    return candidates
