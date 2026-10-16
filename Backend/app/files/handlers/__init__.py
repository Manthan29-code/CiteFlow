from app.files.handlers.base import HANDLERS, DocumentHandler, get_handler, register_handler
from app.files.handlers.pdf import PdfHandler

# Register built-in handlers
register_handler(PdfHandler())

__all__ = ["HANDLERS", "DocumentHandler", "PdfHandler", "get_handler", "register_handler"]
