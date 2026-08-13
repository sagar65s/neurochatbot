"""
Typed exceptions for AI provider failures. The AI Model Manager uses these
types (not string matching on error messages) to decide whether to fall
back to the next provider.
"""


class ProviderError(Exception):
    """Base class for all provider-related errors."""


class RateLimitError(ProviderError):
    """Provider rejected the request due to rate limit / quota."""


class ProviderUnavailableError(ProviderError):
    """Provider is temporarily down, timed out, or returned a 5xx."""


class ProviderConfigError(ProviderError):
    """Provider is missing configuration (e.g. no API key set)."""


class InvalidRequestError(ProviderError):
    """
    The request itself was invalid (bad input, malformed messages, bad
    model name, auth rejected). Must NOT trigger fallback — retrying on
    another provider won't fix it.
    """
