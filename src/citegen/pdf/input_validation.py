from pathlib import Path
from typing import Optional, Union

import pymupdf

from citegen.config import settings


class PdfValidationError(Exception):
    """Base exception for PDF validation failures."""

    pass


class PdfNotFoundError(PdfValidationError):
    """Raised when PDF file does not exist."""

    pass


class PdfInvalidExtensionError(PdfValidationError):
    """Raised when file extension is not .pdf."""

    pass


class PdfEmptyError(PdfValidationError):
    """Raised when PDF file is 0 bytes."""

    pass


class PdfHeaderError(PdfValidationError):
    """Raised when PDF file lacks %PDF header."""

    pass


class PdfOversizedError(PdfValidationError):
    """Raised when PDF file exceeds maximum allowed size in MB."""

    pass


class PdfCorruptedError(PdfValidationError):
    """Raised when PDF file is corrupted or cannot be parsed."""

    pass


class PdfEncryptedError(PdfValidationError):
    """Raised when PDF file is password protected or encrypted."""

    pass


def validate_pdf_input(
    pdf_path: Union[str, Path],
    max_size_mb: Optional[int] = None,
) -> None:
    """
    Validate a PDF file for existence, extension, header, size, integrity, and encryption.

    Raises specific PdfValidationError subclasses on failure.
    """
    path = Path(pdf_path)

    # 1. Existence check
    if not path.is_file():
        raise PdfNotFoundError(f"PDF file does not exist: {path}")

    # 2. Extension check
    if path.suffix.lower() != ".pdf":
        raise PdfInvalidExtensionError(
            f"Invalid file extension '{path.suffix}' for {path.name}; expected '.pdf'"
        )

    # 3. Size check (empty or oversized)
    stat = path.stat()
    if stat.st_size == 0:
        raise PdfEmptyError(f"PDF file is empty (0 bytes): {path}")

    limit_mb = max_size_mb if max_size_mb is not None else settings.max_pdf_size_mb
    max_bytes = limit_mb * 1024 * 1024
    if stat.st_size > max_bytes:
        size_mb = stat.st_size / (1024 * 1024)
        raise PdfOversizedError(
            f"PDF file size ({size_mb:.2f} MB) exceeds maximum allowed size ({limit_mb} MB)"
        )

    # 4. Header check
    with open(path, "rb") as f:
        header = f.read(1024)
    if b"%PDF" not in header[:1024]:
        raise PdfHeaderError(f"File {path.name} does not contain a valid %PDF header")

    # 5. PyMuPDF integrity and encryption check
    try:
        doc = pymupdf.open(path)
    except Exception as e:
        raise PdfCorruptedError(f"Corrupted or invalid PDF file {path.name}: {e}") from e

    try:
        if doc.needs_pass or doc.is_encrypted:
            raise PdfEncryptedError(f"PDF file {path.name} is password-protected or encrypted")
        if doc.page_count < 1:
            raise PdfCorruptedError(f"PDF file {path.name} contains no pages")
        # Attempt to load first page to verify structure
        _ = doc.load_page(0)
    except PdfValidationError:
        raise
    except Exception as e:
        raise PdfCorruptedError(f"Corrupted PDF structure in {path.name}: {e}") from e
    finally:
        doc.close()
