import asyncio
from pathlib import Path
import pymupdf

from app.core.errors import InvalidFileError
from app.files.handlers.base import DocumentHandler


class PdfHandler(DocumentHandler):
    extension: str = "pdf"

    async def validate(self, path: Path) -> None:
        """
        Validates PDF content integrity, headers, and encryption per CLI reference.
        """
        def _sync_validate():
            # 1. Header check
            try:
                with open(path, "rb") as f:
                    header = f.read(1024)
            except Exception as e:
                raise InvalidFileError(f"Could not read file header: {e}")

            if b"%PDF" not in header[:1024]:
                raise InvalidFileError(f"File {path.name} does not contain a valid %PDF header.")

            # 2. PyMuPDF integrity and encryption check
            try:
                doc = pymupdf.open(path)
            except Exception as e:
                raise InvalidFileError(f"Corrupted or unreadable PDF: {e}")

            try:
                if doc.needs_pass or doc.is_encrypted:
                    raise InvalidFileError(f"PDF file is password-protected or encrypted.")
                if doc.page_count < 1:
                    raise InvalidFileError(f"PDF file contains no pages.")
                # Attempt to render/load first page to confirm structure
                _ = doc.load_page(0)
            except InvalidFileError:
                raise
            except Exception as e:
                raise InvalidFileError(f"Corrupted PDF structure: {e}")
            finally:
                doc.close()

        await asyncio.to_thread(_sync_validate)
