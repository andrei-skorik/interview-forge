from collections import deque
from datetime import UTC, datetime, timedelta

import streamlit as st


@st.cache_resource
def get_rate_limiter() -> "RateLimiter":
    return RateLimiter()


class RateLimiter:
    def __init__(self) -> None:
        self.requests: dict[str, deque[datetime]] = {}

    def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Returns True if request is allowed, False if rate limit exceeded."""
        now = datetime.now(tz=UTC)
        window_start = now - timedelta(seconds=window_seconds)

        if key not in self.requests:
            self.requests[key] = deque()

        while self.requests[key] and self.requests[key][0] < window_start:
            self.requests[key].popleft()

        if len(self.requests[key]) >= limit:
            return False

        self.requests[key].append(now)
        return True

    def check_authenticated(self, user_id: str) -> bool:
        return self.check(f"auth:{user_id}", limit=60, window_seconds=60)

    def check_guest(self, ip_hash: str) -> bool:
        return self.check(f"guest:{ip_hash}", limit=20, window_seconds=60)
