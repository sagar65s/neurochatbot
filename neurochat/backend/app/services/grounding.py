"""
Decides whether a user message needs live/current information before
being answered. Two independent signals are checked — either one alone
is enough to trigger grounding:

1. Keyword match — configurable via GROUNDING_KEYWORDS, checked as a
   case-insensitive substring against the message.
2. Recent-year mention — a message mentioning this year or last year
   (e.g. "2026 election result", "budget 2026") is a strong independent
   signal of "current" intent even if no keyword matches, so this catches
   phrasing the keyword list doesn't happen to cover.
"""
import re
from datetime import datetime

from app.config.settings import get_settings

_YEAR_PATTERN = re.compile(r"\b(20[2-9][0-9])\b")


def should_ground(message: str) -> bool:
    settings = get_settings()
    if not settings.enable_search_grounding:
        return False

    text = message.lower()

    if any(keyword in text for keyword in settings.grounding_keywords_list):
        return True

    current_year = datetime.now().year
    for match in _YEAR_PATTERN.findall(text):
        if int(match) >= current_year - 1:
            return True

    return False
