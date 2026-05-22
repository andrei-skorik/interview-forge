import hashlib


def hash_ip(ip_address: str) -> str:
    """SHA-256 hash of IP address for GDPR-compliant logging."""
    return hashlib.sha256(ip_address.encode()).hexdigest()


def hash_user_id(user_id: str) -> str:
    """SHA-256 hash of user_id for audit_log (no PII)."""
    return hashlib.sha256(user_id.encode()).hexdigest()
