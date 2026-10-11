import logging
from pathlib import Path

import pymupdf
import pytest

from citegen.pdf.text_extractor import extract_pdf_text

pytestmark = pytest.mark.part2


def test_page_by_page_text_and_order_preserved(tmp_path: Path):
    pdf_file = tmp_path / "multi_page.pdf"
    doc = pymupdf.open()

    p1 = doc.new_page()
    p1.insert_text(
        pymupdf.Point(50, 100),
        "This is the content on page one of the paper with sufficient characters to pass.",
    )

    p2 = doc.new_page()
    p2.insert_text(
        pymupdf.Point(50, 100),
        "This is the content on page two of the paper with sufficient characters to pass.",
    )

    p3 = doc.new_page()
    p3.insert_text(
        pymupdf.Point(50, 100),
        "This is the content on page three of the paper with sufficient characters to pass.",
    )

    doc.save(str(pdf_file))
    doc.close()

    result = extract_pdf_text(pdf_file)
    assert len(result["page_texts"]) == 3
    assert "page one" in result["page_texts"][0]
    assert "page two" in result["page_texts"][1]
    assert "page three" in result["page_texts"][2]
    assert result["needs_ocr"] is False
    assert len(result["low_text_pages"]) == 0


def test_low_text_pages_flagged(tmp_path: Path):
    pdf_file = tmp_path / "low_text.pdf"
    doc = pymupdf.open()

    # Page 1 has plenty of text
    p1 = doc.new_page()
    p1.insert_text(
        pymupdf.Point(50, 100),
        "This is page one with lots of text to comfortably exceed the minimum threshold.",
    )

    # Page 2 has only a single short word
    p2 = doc.new_page()
    p2.insert_text(pymupdf.Point(50, 100), "Short")

    doc.save(str(pdf_file))
    doc.close()

    result = extract_pdf_text(pdf_file, min_chars_per_page=40)
    assert 1 in result["low_text_pages"]
    assert 0 not in result["low_text_pages"]


def test_image_only_pdf_sets_needs_ocr(tmp_path: Path):
    pdf_file = tmp_path / "scanned.pdf"
    doc = pymupdf.open()
    # Create empty page with no text (simulating pure image/scan)
    _ = doc.new_page()
    doc.save(str(pdf_file))
    doc.close()

    result = extract_pdf_text(pdf_file)
    assert result["needs_ocr"] is True


def test_no_full_text_in_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    secret_text = "VERY_CONFIDENTIAL_PAPER_TEXT_1234567890_SHOULD_NEVER_APPEAR_IN_LOGS"
    pdf_file = tmp_path / "confidential.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), secret_text)
    doc.save(str(pdf_file))
    doc.close()

    with caplog.at_level(logging.DEBUG):
        _ = extract_pdf_text(pdf_file)

    for record in caplog.records:
        assert secret_text not in record.message
