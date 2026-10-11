from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest

from citegen.pdf.ocr import is_tesseract_available, ocr_pdf_pages

pytestmark = [pytest.mark.part2, pytest.mark.ocr]


def test_missing_binary_mocked_gives_clear_message(tmp_path: Path):
    pdf_file = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    _ = doc.new_page()
    doc.save(str(pdf_file))
    doc.close()

    with patch("citegen.pdf.ocr.is_tesseract_available", return_value=False):
        res = ocr_pdf_pages(pdf_file)
        assert res["success"] is False
        assert "Tesseract OCR binary not found" in res["error"]
        assert res["available"] is False


def test_temp_images_removed_even_on_error(tmp_path: Path):
    pdf_file = tmp_path / "temp_clean.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 50), "Test content")
    doc.save(str(pdf_file))
    doc.close()

    # Mock pytesseract.image_to_string to raise an exception
    with patch("citegen.pdf.ocr.is_tesseract_available", return_value=True):
        with patch("pytesseract.image_to_string", side_effect=RuntimeError("OCR failure")):
            res = ocr_pdf_pages(pdf_file)
            assert res["success"] is False
            assert "OCR failure" in res["error"]


def test_image_only_pdf_yields_title_via_tesseract(tmp_path: Path):
    if not is_tesseract_available():
        pytest.skip("Tesseract is not installed on this system")

    pdf_file = tmp_path / "scanned_title.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    # Insert clean large text
    p.insert_text(pymupdf.Point(50, 100), "Plasma Dynamics in Collisionless Flows", fontsize=28)
    doc.save(str(pdf_file))
    doc.close()

    res = ocr_pdf_pages(pdf_file)
    assert res["success"] is True
    assert "Plasma" in res["extracted_text"] or "Dynamics" in res["extracted_text"]
