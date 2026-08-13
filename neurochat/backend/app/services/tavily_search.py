"""
Tavily web search — the single, provider-agnostic grounding mechanism.

Unlike relying on each AI provider's own built-in search tool (Gemini's
google_search, OpenRouter's web plugin — both of which turned out to be
inconsistent and Gemini-specific), this module searches ONCE here, then
the results are injected as plain text context into the conversation
before it's sent to WHICHEVER provider ends up answering — Gemini,
OpenRouter, or Groq. This means:

  - All three providers benefit from grounding equally, not just Gemini.
  - Citations are known upfront (straight from Tavily's response), not
    dependent on a provider's own citation-extraction quirks.
  - Only one extra network call is added (the search itself), not a
    retry loop — keeps response time fast.
"""
from dataclasses import dataclass

import httpx

from app.config.settings import get_settings
from app.providers.base import Citation
from app.utils.logging import get_logger

logger = get_logger(__name__)

TAVILY_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT_SECONDS = 12.0


@dataclass
class SearchResult:
    title: str
    url: str
    content: str


async def search_web(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Calls Tavily's search API. Returns an empty list (never raises) on
    any failure — a search outage should degrade to "answer without
    grounding," not break the whole chat request.
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        logger.warning("Grounding requested but TAVILY_API_KEY is not set — skipping search.")
        return []

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(TAVILY_URL, json=payload)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error("Tavily search failed, continuing without grounding: %s", e)
        return []

    results: list[SearchResult] = []
    for item in data.get("results", []) or []:
        url = item.get("url")
        if not url:
            continue
        results.append(
            SearchResult(
                title=item.get("title") or url,
                url=url,
                content=(item.get("content") or "")[:800],
            )
        )

    logger.info("Tavily returned %d result(s) for query=%r", len(results), query)
    return results


def build_context_message(results: list[SearchResult]) -> str:
    """
    Formats search results into a system-role message that gets appended
    to the conversation history before the AI provider call. Works
    identically regardless of which provider ends up reading it.
    """
    if not results:
        return ""

    lines = ["Live web search results for the user's latest question:\n"]
    for i, r in enumerate(results, start=1):
        lines.append(f"[{i}] {r.title}\nURL: {r.url}\n{r.content}\n")

    lines.append(
        "\nInstructions: base your answer on the search results above rather than "
        "your own prior knowledge, since these are current and your training data "
        "may be outdated. Answer directly and confidently using this information. "
        "Do not mention that you were given search results — just answer naturally."
    )
    return "\n".join(lines)


def results_to_citations(results: list[SearchResult]) -> list[Citation]:
    return [Citation(title=r.title, url=r.url) for r in results]
