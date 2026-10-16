import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request

from app.core.config import settings
from app.core.errors import RateLimitedError


class SimpleRateLimiter:
    """
    In-memory sliding window rate limiter.
    Tracks hits by key and cleans up expired timestamps.
    """

    def __init__(self):
        self._history: Dict[str, List[float]] = defaultdict(list)

    def _parse_rate(self, rate_str: str) -> Tuple[int, int]:
        """Parses rate string like '5/minute', '10/hour', '100/day' into (limit, window_seconds)."""
        parts = rate_str.strip().split("/")
        limit = int(parts[0])
        unit = parts[1].lower() if len(parts) > 1 else "minute"

        unit_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        seconds = unit_seconds.get(unit, 60)
        return limit, seconds

    def check(self, key: str, rate_str: str) -> None:
        """
        Checks if the key has exceeded rate_str.
        Raises RateLimitedError if limit exceeded.
        """
        limit, window = self._parse_rate(rate_str)
        now = time.time()
        window_start = now - window

        # Filter timestamps
        timestamps = [t for t in self._history[key] if t > window_start]
        self._history[key] = timestamps

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(window - (now - oldest)))
            raise RateLimitedError(
                message=f"Too many requests. Please try again in {retry_after} seconds.",
                retry_after=retry_after,
            )

        self._history[key].append(now)


limiter = SimpleRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extracts client IP, respecting FORWARDED_ALLOW_IPS if behind a trusted proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        proxies = [p.strip() for p in settings.FORWARDED_ALLOW_IPS.split(",") if p.strip()]
        client_host = request.client.host if request.client else ""
        if client_host in proxies or "127.0.0.1" in proxies:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"
