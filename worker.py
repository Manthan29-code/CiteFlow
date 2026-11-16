import os
import sys
from pathlib import Path

# Ensure root, Backend, and src directories are in Python path for Cloudflare Workers
ROOT_DIR = Path(__file__).resolve().parent
for directory in [ROOT_DIR, ROOT_DIR / "src", ROOT_DIR / "Backend"]:
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

# Signal serverless mode
os.environ["CLOUDFLARE_WORKER"] = "true"

from app.main import app


class CloudflareEnvMiddleware:
    """
    ASGI middleware that dynamically synchronizes Cloudflare Worker environment
    variables, secrets, and bindings from request.scope["env"] into os.environ.
    This enables existing Pydantic BaseSettings, os.getenv(), and library configs
    to access Cloudflare Dashboard Secrets without modifying core logic.
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and "env" in scope:
            env = scope["env"]
            for attr in dir(env):
                if not attr.startswith("_"):
                    try:
                        val = getattr(env, attr, None)
                        if isinstance(val, (str, int, float, bool)):
                            os.environ[attr] = str(val)
                    except Exception:
                        pass
        await self.asgi_app(scope, receive, send)


# Expose ASGI entrypoint for Cloudflare Python Workers
try:
    from workers import asgi

    Default = asgi.entrypoint(CloudflareEnvMiddleware(app))
except ImportError:
    # Fallback for local testing or standard ASGI servers (e.g. uvicorn)
    Default = CloudflareEnvMiddleware(app)
