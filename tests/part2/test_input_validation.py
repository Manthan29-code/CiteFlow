from pathlib import Path

import pymupdf
import pytest

from citegen.pdf.input_validation import (
    PdfCorruptedError,
    PdfEmptyError,
    PdfEncryptedError,
    PdfHeaderError,
    PdfInvalidExtensionError,
    PdfNotFoundError,
    PdfOversizedError,
    validate_pdf_input,
)

pytestmark = pytest.mark.part2


def test_missing_file_raises_not_found(tmp_path: Path):
    missing_file = tmp_path / "non_existent.pdf"
    with pytest.raises(PdfNotFoundError) as exc_info:
        validate_pdf_input(missing_file)
    assert "does not exist" in str(exc_info.value)


def test_wrong_extension_raises_invalid_extension(tmp_path: Path):
    txt_file = tmp_path / "document.txt"
    txt_file.write_text("Hello world", encoding="utf-8")
    with pytest.raises(PdfInvalidExtensionError) as exc_info:
        validate_pdf_input(txt_file)
    assert "Invalid file extension" in str(exc_info.value)
    assert ".txt" in str(exc_info.value)


def test_empty_file_raises_empty_error(tmp_path: Path):
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")
    with pytest.raises(PdfEmptyError) as exc_info:
        validate_pdf_input(empty_pdf)
    assert "0 bytes" in str(exc_info.value)


def test_bad_header_raises_header_error(tmp_path: Path):
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"NOT A REAL PDF FILE HEADER DATA 12345")
    with pytest.raises(PdfHeaderError) as exc_info:
        validate_pdf_input(fake_pdf)
    assert "%PDF header" in str(exc_info.value)


def test_corrupted_pdf_raises_corrupted_error(tmp_path: Path):
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(
        b"%PDF-1.4\ncorrupted junk bytes that cannot be parsed as a valid pdf trailer"
    )
    with pytest.raises(PdfCorruptedError) as exc_info:
        validate_pdf_input(corrupt_pdf)
    assert "Corrupted" in str(exc_info.value) or "invalid" in str(exc_info.value)


def test_password_protected_pdf_raises_encrypted_error(tmp_path: Path):
    enc_pdf = tmp_path / "protected.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(pymupdf.Point(50, 50), "Secret encrypted paper")
    doc.save(
        str(enc_pdf),
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        user_pw="user123",
        owner_pw="owner123",
    )
    doc.close()

    with pytest.raises(PdfEncryptedError) as exc_info:
        validate_pdf_input(enc_pdf)
    assert "password-protected" in str(exc_info.value) or "encrypted" in str(exc_info.value)


def test_oversized_pdf_raises_oversized_error(tmp_path: Path):
    normal_pdf = tmp_path / "normal.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(pymupdf.Point(50, 50), "A normal document")
    doc.save(str(normal_pdf))
    doc.close()

    # Pass max_size_mb = 0 to trigger oversized validation
    with pytest.raises(PdfOversizedError) as exc_info:
        validate_pdf_input(normal_pdf, max_size_mb=0)
    assert "exceeds maximum allowed size" in str(exc_info.value)
