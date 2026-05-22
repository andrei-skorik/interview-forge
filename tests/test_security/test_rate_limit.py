"""Tests for RateLimiter.

Tests use RateLimiter directly (not via get_rate_limiter() which requires
@st.cache_resource), to avoid the Streamlit dependency in unit tests.
"""

from datetime import UTC, datetime, timedelta

from lib.utils.rate_limit import RateLimiter


def _make_limiter() -> RateLimiter:
    """Return a fresh RateLimiter instance for each test."""
    return RateLimiter()


def test_first_request_within_limit_passes() -> None:
    """The first request for any key must be allowed."""
    limiter = _make_limiter()
    assert limiter.check("user:test1", limit=5, window_seconds=60) is True


def test_requests_up_to_limit_all_pass() -> None:
    """All N requests within the window must pass."""
    limiter = _make_limiter()
    limit = 5
    for i in range(limit):
        result = limiter.check("user:burst", limit=limit, window_seconds=60)
        assert result is True, f"Request {i + 1} should pass (limit={limit})"


def test_n_plus_one_request_is_blocked() -> None:
    """The (N+1)th request must be rejected when the window has N slots."""
    limiter = _make_limiter()
    limit = 5
    for _ in range(limit):
        limiter.check("user:overflow", limit=limit, window_seconds=60)

    # This is the (limit+1)th request — must be blocked
    result = limiter.check("user:overflow", limit=limit, window_seconds=60)
    assert result is False


def test_different_keys_are_independent() -> None:
    """Rate limit state must be isolated per key."""
    limiter = _make_limiter()
    limit = 2
    for _ in range(limit):
        limiter.check("key_a", limit=limit, window_seconds=60)

    # key_a is exhausted, but key_b is fresh
    assert limiter.check("key_a", limit=limit, window_seconds=60) is False
    assert limiter.check("key_b", limit=limit, window_seconds=60) is True


def test_window_expiry_allows_new_requests() -> None:
    """After the window expires, the same key should be allowed again."""
    limiter = _make_limiter()
    limit = 3
    window_seconds = 1  # very short window for testing

    # Fill up the limit
    for _ in range(limit):
        limiter.check("key:expiry", limit=limit, window_seconds=window_seconds)

    # Immediately blocked
    assert limiter.check("key:expiry", limit=limit, window_seconds=window_seconds) is False

    # Manually expire all timestamps by backdating them

    key = "key:expiry"
    old_time = datetime.now(tz=UTC) - timedelta(seconds=window_seconds + 1)
    for i in range(len(limiter.requests[key])):
        limiter.requests[key][i] = old_time

    # Now should pass again
    assert limiter.check("key:expiry", limit=limit, window_seconds=window_seconds) is True


def test_check_authenticated_uses_60_per_minute_limit() -> None:
    """check_authenticated should allow 60 requests then block the 61st."""
    limiter = _make_limiter()
    user_id = "user-uuid-authenticated-001"

    for i in range(60):
        result = limiter.check_authenticated(user_id)
        assert result is True, f"Authenticated request {i + 1} should pass"

    # 61st must be blocked
    assert limiter.check_authenticated(user_id) is False


def test_check_guest_uses_20_per_minute_limit() -> None:
    """check_guest should allow 20 requests then block the 21st."""
    limiter = _make_limiter()
    ip_hash = "abc123def456" * 3  # some ip_hash string

    for i in range(20):
        result = limiter.check_guest(ip_hash)
        assert result is True, f"Guest request {i + 1} should pass"

    # 21st must be blocked
    assert limiter.check_guest(ip_hash) is False


def test_authenticated_and_guest_limits_are_different() -> None:
    """Authenticated limit (60) must be higher than guest limit (20)."""
    limiter_auth = _make_limiter()
    limiter_guest = _make_limiter()

    user_id = "user-auth-compare"
    ip_hash = "ip-hash-compare"

    # Guest exhausts after 20
    for _ in range(20):
        limiter_guest.check_guest(ip_hash)
    assert limiter_guest.check_guest(ip_hash) is False

    # Authenticated still has capacity past 20
    for _ in range(21):
        limiter_auth.check_authenticated(user_id)
    assert limiter_auth.check_authenticated(user_id) is True


def test_rate_limiter_initializes_empty() -> None:
    """A new RateLimiter must start with an empty requests dict."""
    limiter = _make_limiter()
    assert limiter.requests == {}


def test_rate_limiter_populates_key_on_first_check() -> None:
    """After the first check, the key must appear in requests dict."""
    limiter = _make_limiter()
    limiter.check("new_key", limit=10, window_seconds=60)
    assert "new_key" in limiter.requests
    assert len(limiter.requests["new_key"]) == 1
