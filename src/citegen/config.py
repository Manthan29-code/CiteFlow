import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load from .env if present
load_dotenv()


class Settings:
    def __init__(
        self,
        crossref_mailto: Optional[str] = None,
        openalex_api_key: Optional[str] = None,
        request_timeout_seconds: Optional[float] = None,
        output_dir: Optional[str] = None,
        grobid_url: Optional[str] = None,
        max_pdf_size_mb: Optional[int] = None,
        ocr_enabled: Optional[bool] = None,
    ):
        self.crossref_mailto: Optional[str] = (
            crossref_mailto
            if crossref_mailto is not None
            else os.getenv("CROSSREF_MAILTO", "") or None
        )
        self.openalex_api_key: Optional[str] = (
            openalex_api_key
            if openalex_api_key is not None
            else os.getenv("OPENALEX_API_KEY", "") or None
        )
        self.request_timeout_seconds: float = float(
            request_timeout_seconds
            if request_timeout_seconds is not None
            else os.getenv("REQUEST_TIMEOUT_SECONDS", "15")
        )
        self.output_dir: Path = Path(
            output_dir if output_dir is not None else os.getenv("OUTPUT_DIR", "./output")
        )
        self.grobid_url: str = (
            grobid_url
            if grobid_url is not None
            else os.getenv("GROBID_URL", "http://localhost:8070")
        )
        self.max_pdf_size_mb: int = int(
            max_pdf_size_mb if max_pdf_size_mb is not None else os.getenv("MAX_PDF_SIZE_MB", "50")
        )
        ocr_env = os.getenv("OCR_ENABLED", "true").lower()
        self.ocr_enabled: bool = (
            ocr_enabled if ocr_enabled is not None else (ocr_env in ("1", "true", "yes", "on"))
        )


settings = Settings()
