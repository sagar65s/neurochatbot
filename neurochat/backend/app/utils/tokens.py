"""
Approximate token estimation without pulling in a full tokenizer
dependency. ~4 characters per token is a reasonable average for
English-heavy chat text — good enough to bound context size safely.
Swap for a real tokenizer later without changing any caller.
"""

CHARS_PER_TOKEN_ESTIMATE = 4


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)
