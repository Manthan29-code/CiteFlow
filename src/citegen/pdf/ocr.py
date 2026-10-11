import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Union

import pymupdf

logger = logging.getLogger(__name__)


def is_tesseract_available() -> bool:
    """Check if Tesseract binary is available on system PATH."""
    try:
        import pytesseract

        # Check either shutil.which or get_tesseract_version
        if shutil.which("tesseract"):
            return True
        ver = pytesseract.get_tesseract_version()
        return bool(ver)
    except Exception:
        return False


def ocr_pdf_pages(
    pdf_path: Union[str, Path],
    max_pages: int = 3,
) -> Dict[str, Any]:
    """
    Render PDF pages to images and run Tesseract OCR.

    Guarantees temporary image files are deleted even if errors occur.
    Returns structured result dict.
    """
    path = Path(pdf_path)
    if not path.is_file():
        return {
            "success": False,
            "error": f"File does not exist: {path}",
            "available": False,
            "page_texts": [],
            "extracted_text": "",
        }

    # Verify tesseract availability
    if not is_tesseract_available():
        return {
            "success": False,
            "error": "Tesseract OCR binary not found on PATH. Install Tesseract to enable OCR.",
            "available": False,
            "page_texts": [],
            "extracted_text": "",
        }

    import pytesseract

    page_texts: List[str] = []
    doc = pymupdf.open(path)

    try:
        num_pages_to_ocr = min(doc.page_count, max_pages)

        # Use temporary directory to guarantee cleanup
        with tempfile.TemporaryDirectory(prefix="citeflow_ocr_") as tmp_dir:
            tmp_path = Path(tmp_dir)

            for page_idx in range(num_pages_to_ocr):
                page = doc.load_page(page_idx)
                # Render to high-DPI pixmap for reliable OCR
                pix = page.get_pixmap(dpi=150)
                img_file = tmp_path / f"page_{page_idx}.png"
                pix.save(str(img_file))

                # Run tesseract
                text = pytesseract.image_to_string(str(img_file)) or ""
                page_texts.append(text)

        combined = "\n\n".join(page_texts)
        return {
            "success": True,
            "error": None,
            "available": True,
            "page_texts": page_texts,
            "extracted_text": combined,
        }

    except Exception as exc:
        logger.warning("OCR processing failed for %s: %s", path.name, exc)
        return {
            "success": False,
            "error": f"OCR processing failed: {exc}",
            "available": True,
            "page_texts": [],
            "extracted_text": "",
        }
    finally:
        doc.close()
