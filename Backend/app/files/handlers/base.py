from pathlib import Path
from typing import Dict, Protocol


class DocumentHandler(Protocol):
    extension: str

    async def validate(self, path: Path) -> None:
        """
        Validates file content. Raises InvalidFileError on encrypted, corrupted,
        or malformed documents.
        """
        ...


# Global registry of document handlers
HANDLERS: Dict[str, DocumentHandler] = {}


def register_handler(handler: DocumentHandler) -> None:
    """Registers a handler for its specified extension."""
    HANDLERS[handler.extension.lower()] = handler


def get_handler(extension: str) -> DocumentHandler | None:
    """Retrieves the handler for a given extension."""
    return HANDLERS.get(extension.lower().lstrip("."))
