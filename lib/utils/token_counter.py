import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")
CONTEXT_LIMIT = 32_000
SUMMARIZE_THRESHOLD = 30_000


def count_tokens(text: str) -> int:
    """Count tokens using cl100k_base (GPT-4/5 family)."""
    return len(_ENCODING.encode(text))


def count_messages_tokens(messages: list[dict[str, str]]) -> int:
    """Count total tokens across a messages list."""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""))
        total += 4  # per-message overhead
    return total + 2  # conversation overhead


def exceeds_context_limit(messages: list[dict[str, str]]) -> bool:
    return count_messages_tokens(messages) > SUMMARIZE_THRESHOLD
