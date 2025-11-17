"""LLM provider abstraction layer."""

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from derivatives_gpt_core.config import get_settings
from derivatives_gpt_core.exceptions import MissingAPIKeyError, InvalidConfigError
from typing import Literal


def get_base_llm(
    temperature: float = 0.0,
    model_override: str | None = None,
    provider_override: Literal["openai", "gemini", "gemini_finetuned", "openrouter"] | None = None,
    streaming: bool = False
) -> BaseChatModel:
    """
    Get configured base LLM instance.

    This is the foundation function that all specialized LLM getters call.
    Prefer using specialized functions (get_classification_llm, get_planner_llm, etc.)
    unless you need custom temperature or model overrides.

    Args:
        temperature: Sampling temperature (0=deterministic, 1=creative)
        model_override: Override configured model name
        provider_override: Override configured provider (openai, gemini, etc.)
        streaming: Enable streaming mode for token-by-token generation

    Returns:
        Configured LangChain chat model instance

    Raises:
        ValueError: If API key missing or provider unknown
    """
    settings = get_settings()
    llm_provider_name = provider_override or settings.llm_provider

    if llm_provider_name == "openai":
        if not settings.openai_api_key:
            raise MissingAPIKeyError(
                "OpenAI API key not configured. Set OPENAI_API_KEY in .env",
                details={"provider": "openai"}
            )

        return ChatOpenAI(
            model=model_override or settings.openai_model,
            temperature=temperature,
            api_key=settings.openai_api_key,
            streaming=streaming
        )

    elif llm_provider_name in ("gemini", "gemini_finetuned"):
        if not settings.gemini_api_key:
            raise MissingAPIKeyError(
                "Gemini API key not configured. Set GEMINI_API_KEY in .env",
                details={"provider": "gemini"}
            )

        model_name = model_override or (
            settings.gemini_finetuned_model if llm_provider_name == "gemini_finetuned"
            else settings.gemini_model
        )

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=settings.gemini_api_key,
            streaming=streaming
        )

    elif llm_provider_name == "openrouter":
        if not settings.openrouter_api_key:
            raise MissingAPIKeyError(
                "OpenRouter API key not configured. Set OPENROUTER_API_KEY in .env",
                details={"provider": "openrouter"}
            )

        return ChatOpenAI(
            model=model_override or settings.openrouter_model,
            temperature=temperature,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            streaming=streaming
        )

    else:
        raise InvalidConfigError(
            f"Unknown LLM provider: {llm_provider_name}",
            details={
                "provider": llm_provider_name,
                "valid_providers": ["openai", "gemini", "gemini_finetuned", "openrouter"]
            }
        )


def get_classification_llm(streaming: bool = False) -> BaseChatModel:
    """
    Get LLM for classification with slight creativity for edge cases.

    Temperature=0.3 allows handling ambiguous queries while maintaining
    consistency in classification decisions.

    Args:
        streaming: Enable streaming mode for token-by-token generation
    """
    settings = get_settings()

    if settings.llm_provider == "openai":
        return get_base_llm(temperature=0.3, model_override=settings.classification_openai_model, streaming=streaming)
    elif settings.llm_provider == "openrouter":
        return get_base_llm(temperature=0.3, model_override=settings.classification_openrouter_model, streaming=streaming)
    else:
        return get_base_llm(temperature=0.3, model_override=settings.classification_gemini_model, streaming=streaming)


def get_planner_llm() -> BaseChatModel:
    """
    Get LLM for execution planning (deterministic).

    Temperature=0.0 ensures consistent plans for same inputs.
    """
    settings = get_settings()

    if settings.llm_provider == "openai":
        return get_base_llm(temperature=0.0, model_override=settings.planner_openai_model)
    elif settings.llm_provider == "openrouter":
        return get_base_llm(temperature=0.0, model_override=settings.planner_openrouter_model)
    else:
        return get_base_llm(temperature=0.0, model_override=settings.planner_gemini_model)


def get_decomposer_llm() -> BaseChatModel:
    """
    Get LLM for mathematical feature extraction (deterministic).

    Temperature=0.0 ensures exact parameter extraction without randomness.
    """
    settings = get_settings()

    if settings.llm_provider == "openai":
        return get_base_llm(temperature=0.0, model_override=settings.decomposer_openai_model)
    elif settings.llm_provider == "openrouter":
        return get_base_llm(temperature=0.0, model_override=settings.decomposer_openrouter_model)
    else:
        return get_base_llm(temperature=0.0, model_override=settings.decomposer_gemini_model)


def get_validator_llm() -> BaseChatModel:
    """
    Get LLM for parameter validation (deterministic).

    Temperature=0.0 ensures strict, consistent validation decisions.
    """
    settings = get_settings()

    if settings.llm_provider == "openai":
        return get_base_llm(temperature=0.0, model_override=settings.validator_openai_model)
    elif settings.llm_provider == "openrouter":
        return get_base_llm(temperature=0.0, model_override=settings.validator_openrouter_model)
    else:
        return get_base_llm(temperature=0.0, model_override=settings.validator_gemini_model)


def get_narrator_llm() -> BaseChatModel:
    """
    Get LLM for narration with slight creativity for natural language flow.

    Temperature=0.3 allows fluent narrative while staying factually accurate.
    """
    settings = get_settings()

    if settings.llm_provider == "openai":
        return get_base_llm(temperature=0.3, model_override=settings.openai_model)
    elif settings.llm_provider == "openrouter":
        return get_base_llm(temperature=0.3, model_override=settings.openrouter_model)
    else:
        return get_base_llm(temperature=0.3, model_override=settings.gemini_model)


def get_pricing_llm() -> BaseChatModel:
    """
    Get configured LLM for pricing calculations.

    Temperature=0.1 provides minimal randomness while maintaining numerical stability.
    """
    return get_base_llm(temperature=0.1)


def get_judge_llm() -> BaseChatModel:
    """
    Get LLM for evaluation judging (deterministic).

    Uses same model as base by default for cost efficiency.
    For production, consider using a higher-quality model for more objective evaluation.

    Temperature=0.0 ensures consistent scoring across evaluations.
    """
    settings = get_settings()

    # Use same provider/model as base for now (configurable later)
    return get_base_llm(temperature=0.0)
