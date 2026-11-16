import asyncio
import logging
from pathlib import Path

try:
    import pymupdf
except ImportError:
    pymupdf = None

try:
    import pypdf
except ImportError:
    pypdf = None

from app.core.errors import InvalidFileError
from app.files.handlers.base import DocumentHandler

logger = logging.getLogger(__name__)


class PdfHandler(DocumentHandler):
    extension: str = "pdf"

    async def validate(self, path: Path) -> None:
        """
        Validates PDF content integrity, headers, and encryption per CLI reference.
        Uses PyMuPDF if available, with pure-Python pypdf fallback for WebAssembly / serverless.
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

            # 2. PDF integrity and encryption check
            if pymupdf is not None:
                try:
                    doc = pymupdf.open(path)
                except Exception as e:
                    raise InvalidFileError(f"Corrupted or unreadable PDF: {e}")

                try:
                    if doc.needs_pass or doc.is_encrypted:
                        raise InvalidFileError("PDF file is password-protected or encrypted.")
                    if doc.page_count < 1:
                        raise InvalidFileError("PDF file contains no pages.")
                    # Attempt to render/load first page to confirm structure
                    _ = doc.load_page(0)
                except InvalidFileError:
                    raise
                except Exception as e:
                    raise InvalidFileError(f"Corrupted PDF structure: {e}")
                finally:
                    doc.close()
            elif pypdf is not None:
                try:
                    reader = pypdf.PdfReader(str(path))
                    if reader.is_encrypted:
                        raise InvalidFileError("PDF file is password-protected or encrypted.")
                    if len(reader.pages) < 1:
                        raise InvalidFileError("PDF file contains no pages.")
                except InvalidFileError:
                    raise
                except Exception as e:
                    raise InvalidFileError(f"Corrupted PDF structure: {e}")

        await asyncio.to_thread(_sync_validate)

    async def title_candidates(self, path: Path) -> list[dict]:
        """
        Extracts ranked title candidates using GROBID and PyMuPDF layout heuristics.
        """
        try:
            from citegen.pdf.title_detector import detect_title_candidates
            return await detect_title_candidates(path)
        except ImportError as e:
            logger.warning("Optional PDF title detector not available: %s", e)
            return []
