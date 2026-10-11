import logging
from pathlib import Path
from typing import Any, Dict, List, Union

import pymupdf

logger = logging.getLogger(__name__)


def extract_pdf_text(
    pdf_path: Union[str, Path],
    min_chars_per_page: int = 50,
) -> Dict[str, Any]:
    """
    Extract text page by page from a PDF document.

    Preserves page order and identifies low-text pages.
    Flags needs_ocr if the overall text is inadequate.
    Never logs full extracted text.
    """
    path = Path(pdf_path)
    doc = pymupdf.open(path)

    page_texts: List[str] = []
    low_text_pages: List[int] = []

    try:
        total_pages = doc.page_count
        logger.debug("Extracting text from %s (%d pages)", path.name, total_pages)

        for page_idx in range(total_pages):
            page = doc.load_page(page_idx)
            text = page.get_text("text") or ""
            page_texts.append(text)

            # Strip whitespace to measure genuine text content
            clean_page_chars = len("".join(text.split()))
            if clean_page_chars < min_chars_per_page:
                low_text_pages.append(page_idx)

        combined_text = "\n\n".join(page_texts)
        total_clean_chars = len("".join(combined_text.split()))

        # If document has pages but total clean text is under threshold or all pages are low text
        needs_ocr = total_clean_chars < min_chars_per_page or (
            len(low_text_pages) == total_pages and total_pages > 0
        )

        logger.debug(
            "Extracted %d characters across %d pages (low-text pages: %d, needs_ocr: %s)",
            total_clean_chars,
            total_pages,
            len(low_text_pages),
            needs_ocr,
        )

        return {
            "page_texts": page_texts,
            "extracted_text": combined_text,
            "low_text_pages": low_text_pages,
            "needs_ocr": needs_ocr,
            "page_count": total_pages,
        }
    finally:
        doc.close()
