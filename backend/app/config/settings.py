"""
Centralized application settings loaded from environment variables.
Uses pydantic-settings so missing/invalid config fails fast and loudly
at startup instead of causing confusing errors later.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Firebase Admin ---
    firebase_project_id: str
    firebase_client_email: str
    firebase_private_key: str

    # --- AI providers ---
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None

    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None

    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None

    ai_provider_order: str = "gemini,openrouter,groq"

    # --- Conversation memory / context management ---
    max_history_messages: int = 20
    max_context_tokens: int = 6000
    system_prompt: Optional[str] = (
        "You are NeuroChat, a helpful, concise AI assistant. "
        "Use markdown formatting (including code blocks with language tags) where it helps."
    )

    # --- Security / rate limiting ---
    max_request_body_bytes: int = 32_000
    chat_rate_limit_requests: int = 20
    chat_rate_limit_window_seconds: int = 60

    # --- Web search grounding (Tavily — provider-agnostic) ---
    enable_search_grounding: bool = True
    tavily_api_key: Optional[str] = None
    grounding_keywords: str = (
        "today,current,currently,latest,recent,recently,this week,this month,"
        "this year,right now,at present,presently,as of now,breaking news,"
        "news,live score,live,update,updates,status now,ippo,ipo,"
        "stock price,share price,exchange rate,gold rate,gold price,"
        "petrol price,diesel price,weather,forecast,temperature today,"
        "who is the,who is current,cm of,cm yaru,yaru cm,chief minister,"
        "prime minister,president of,governor of,election result,"
        "election results,winner of,match score,today match,world cup,"
        "as of today,up to date,up-to-date,new release,just announced,"
        "trending,viral,ipl,box office,release date"
    )

    # --- App config ---
    database_type: str = "firestore"
    frontend_url: str = "http://localhost:3000"

    @property
    def provider_order_list(self) -> List[str]:
        return [p.strip() for p in self.ai_provider_order.split(",") if p.strip()]

    @property
    def grounding_keywords_list(self) -> List[str]:
        return [k.strip().lower() for k in self.grounding_keywords.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
