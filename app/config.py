from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM - canonical name LLM_MODEL (fix LM_MODEL typo)
    google_api_key: str = Field(default="your_gemini_api_key_here", alias="GOOGLE_API_KEY")
    llm_model: str = Field(default="gemini-1.5-flash", alias="LLM_MODEL")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")

    # DB - single source, sqlite fallback for dev, postgres for prod
    database_url: str = Field(default="sqlite:///./data/app.db", alias="DATABASE_URL")

    # RAG - ChromaDB only (single vector store)
    chroma_persist_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIR")

    # Memory cache
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")

    # MCP - explicit mode
    enable_mcp: bool = Field(default=False, alias="ENABLE_MCP")
    mcp_execution_mode: str = Field(default="direct", alias="MCP_EXECUTION_MODE")  # mcp | direct

    # Observability
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    enable_guardrails: bool = Field(default=True, alias="ENABLE_GUARDRAILS")

    # Auth - JWT
    jwt_secret: str = Field(default="dev-secret-change-me-please-use-env", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60*24, alias="JWT_EXPIRE_MINUTES")

    # Compatibility: map legacy LM_MODEL -> LLM_MODEL if present
    def model_post_init(self, __context):
        import os
        # handle typo LM_MODEL
        if os.getenv("LM_MODEL") and not os.getenv("LLM_MODEL"):
            object.__setattr__(self, "llm_model", os.getenv("LM_MODEL"))

    @property
    def sync_database_url(self) -> str:
        url = self.database_url
        # handle sqlite+aiosqlite -> sqlite
        url = url.replace("sqlite+aiosqlite", "sqlite")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    @property
    def is_postgres(self) -> bool:
        return self.sync_database_url.startswith("postgresql")

settings = Settings()
