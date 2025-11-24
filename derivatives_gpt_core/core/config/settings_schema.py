"""
Application settings schema.

Defines Pydantic Settings model for configuration loaded from environment variables.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import Literal


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Organized into categories:
    - LLM Providers: API keys and model names
    - LangSmith: Observability configuration
    - Pricing: Default rates and calculations
    - RAG: Retrieval settings
    - Checkpointing: Conversation persistence
    - Web Search: External augmentation

    Note: .env file is pre-loaded at module import time to avoid blocking I/O
    in async contexts (see settings_singleton.py).
    """

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore"
    )

    # === LLM PROVIDER ===
    llm_provider: Literal["openai", "gemini", "gemini_finetuned", "openrouter"] = Field(
        default="openai",
        description="LLM provider selection"
    )

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model")

    # Google/Gemini
    gemini_api_key: str = Field(default="", description="Gemini API key")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model")
    gemini_finetuned_model: str = Field(default="", description="Fine-tuned Gemini model")

    # OpenRouter
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    openrouter_model: str = Field(
        default="anthropic/claude-3-haiku:beta",
        description="OpenRouter model name"
    )

    # GCP
    gcp_project_id: str = Field(default="", description="GCP project ID")
    gcp_bucket_name: str = Field(default="", description="GCS bucket name")
    data_source: Literal["mock", "gcp"] = Field(default="mock", description="Data source")

    # === LANGSMITH OBSERVABILITY ===
    langsmith_api_key: str = Field(default="", description="LangSmith API key")
    langsmith_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        description="LangSmith API endpoint"
    )
    langsmith_project: str = Field(
        default="derivatives-gpt",
        description="LangSmith project"
    )
    enable_langsmith: bool = Field(default=True, description="Enable tracing")

    # LangSmith Tagging
    langsmith_tag_product_type: bool = Field(default=True, description="Tag with product_type")
    langsmith_tag_asset_class: bool = Field(default=True, description="Tag with asset_class")
    langsmith_tag_pricing_method: bool = Field(default=True, description="Tag with pricing_method")
    langsmith_tag_ticker: bool = Field(default=False, description="Tag with ticker (privacy)")

    # LangSmith Metrics
    langsmith_track_metrics: bool = Field(default=True, description="Track performance metrics")

    # === PRICING CONFIGURATION ===
    default_risk_free_rate: float = Field(
        default=0.05,
        description="Default risk-free rate",
        ge=0.0,
        le=1.0
    )
    days_per_year: int = Field(
        default=365,
        description="Days per year for conversion",
        ge=1,
        le=366
    )

    # Treasury Rate Fallbacks (updated monthly from treasury.gov)
    risk_free_rate_1month: float = Field(default=0.0540, description="1-month T-bill rate")
    risk_free_rate_3month: float = Field(default=0.0525, description="3-month T-bill rate")
    risk_free_rate_6month: float = Field(default=0.0510, description="6-month T-bill rate")
    risk_free_rate_1year: float = Field(default=0.0495, description="1-year T-bill rate")
    risk_free_rate_default: float = Field(default=0.0480, description="Default T-bill rate")

    # === RAG SETTINGS ===
    rag_enabled: bool = Field(default=True, description="Enable RAG retrieval")
    rag_index_path: str = Field(
        default="databases/vectorstore/rag_index_structured.faiss",
        description="Path to FAISS index"
    )
    rag_metadata_path: str = Field(
        default="databases/vectorstore/metadata_structured.json",
        description="Path to metadata JSON"
    )
    rag_bm25_candidate_count: int = Field(
        default=20,
        description="BM25 keyword matches"
    )
    rag_rerank_candidate_count: int = Field(
        default=10,
        description="Candidates to rerank with embeddings"
    )
    rag_final_source_count: int = Field(
        default=3,
        description="Final sources to return"
    )
    rag_embedding_model: str = Field(
        default="models/text-embedding-004",
        description="Google embedding model"
    )

    # === SPECIALIZED NODE MODELS ===
    # Classification
    classification_openai_model: str = Field(default="")
    classification_gemini_model: str = Field(default="")
    classification_openrouter_model: str = Field(default="")

    # Planning
    planner_openai_model: str = Field(default="")
    planner_gemini_model: str = Field(default="")
    planner_openrouter_model: str = Field(default="")

    # Decomposition
    decomposer_openai_model: str = Field(default="")
    decomposer_gemini_model: str = Field(default="")
    decomposer_openrouter_model: str = Field(default="")

    # Validation
    validator_openai_model: str = Field(default="")
    validator_gemini_model: str = Field(default="")
    validator_openrouter_model: str = Field(default="")

    # === AGENT BEHAVIOR ===
    max_agent_iterations: int = Field(
        default=10,
        description="Maximum tool calling iterations",
        ge=1,
        le=50
    )

    # === CHECKPOINTING ===
    checkpoint_db_path: Path = Field(
        default=Path("data/checkpoints/checkpoints.db"),
        description="SQLite checkpoint database path"
    )

    # === WEB SEARCH ===
    enable_web_search: bool = Field(default=True, description="Enable web search augmentation")
    tavily_api_key: str = Field(default="", description="Tavily API key")

    @model_validator(mode='after')
    def set_specialized_model_defaults(self):
        """
        Auto-populate specialized model fields with main provider model if not explicitly set.

        This ensures DRY configuration - you only need to set the main model
        (e.g., OPENROUTER_MODEL) and all specialized nodes inherit it unless overridden.

        Example:
            OPENROUTER_MODEL=google/gemini-2.5-flash-lite
            → classification_openrouter_model defaults to google/gemini-2.5-flash-lite
            → planner_openrouter_model defaults to google/gemini-2.5-flash-lite
            → etc.

        You can still override individual nodes:
            CLASSIFICATION_OPENROUTER_MODEL=anthropic/claude-3-5-sonnet
        """
        # OpenAI models
        if not self.classification_openai_model:
            self.classification_openai_model = self.openai_model
        if not self.planner_openai_model:
            self.planner_openai_model = self.openai_model
        if not self.decomposer_openai_model:
            self.decomposer_openai_model = self.openai_model
        if not self.validator_openai_model:
            self.validator_openai_model = self.openai_model

        # Gemini models
        if not self.classification_gemini_model:
            self.classification_gemini_model = self.gemini_model
        if not self.planner_gemini_model:
            self.planner_gemini_model = self.gemini_model
        if not self.decomposer_gemini_model:
            self.decomposer_gemini_model = self.gemini_model
        if not self.validator_gemini_model:
            self.validator_gemini_model = self.gemini_model

        # OpenRouter models
        if not self.classification_openrouter_model:
            self.classification_openrouter_model = self.openrouter_model
        if not self.planner_openrouter_model:
            self.planner_openrouter_model = self.openrouter_model
        if not self.decomposer_openrouter_model:
            self.decomposer_openrouter_model = self.openrouter_model
        if not self.validator_openrouter_model:
            self.validator_openrouter_model = self.openrouter_model

        return self
