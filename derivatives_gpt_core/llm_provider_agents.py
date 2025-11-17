"""
Agent-Specific LLM Providers
=============================
Specialized LLM configurations for educational and pricing agents with
appropriate temperatures and model selection.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from typing import Literal, Optional
import logging

from derivatives_gpt_core.llm_provider import get_base_llm
from derivatives_gpt_core.core.state.agent_state_wrapper import AgentType

logger = logging.getLogger(__name__)


# ============================================================================
# EDUCATIONAL AGENT LLMs
# ============================================================================

def get_educational_llm(
    task: Literal["explanation", "assessment", "verification", "rewrite"] = "explanation",
    temperature: Optional[float] = None
) -> BaseChatModel:
    """
    Get LLM configured for educational agent tasks.

    Educational agent needs higher temperature for creative, engaging explanations.

    Task-specific defaults:
    - explanation: 0.7 (creative, varied explanations)
    - assessment: 0.3 (consistent quality evaluation)
    - verification: 0.5 (balanced question generation)
    - rewrite: 0.8 (creative improvements)

    Args:
        task: Educational task type
        temperature: Override temperature, or None for task default

    Returns:
        Configured LLM instance
    """
    # Task-specific temperature defaults
    defaults = {
        "explanation": 0.7,
        "assessment": 0.3,
        "verification": 0.5,
        "rewrite": 0.8
    }

    temp = temperature if temperature is not None else defaults[task]

    logger.debug(f"Educational LLM for '{task}' task (temp={temp})")
    return get_base_llm(temperature=temp)


def get_explanation_generator_llm() -> BaseChatModel:
    """
    LLM for generating educational explanations.

    Higher temperature (0.7) for creative, engaging, varied explanations.
    """
    return get_educational_llm("explanation", 0.7)


def get_explanation_critic_llm() -> BaseChatModel:
    """
    LLM for assessing explanation quality.

    Lower temperature (0.3) for consistent, objective evaluation.
    """
    return get_educational_llm("assessment", 0.3)


def get_verification_llm() -> BaseChatModel:
    """
    LLM for generating verification questions.

    Medium temperature (0.5) for balanced question variety.
    """
    return get_educational_llm("verification", 0.5)


def get_rewriter_llm() -> BaseChatModel:
    """
    LLM for rewriting low-quality explanations.

    Higher temperature (0.8) for creative improvements.
    """
    return get_educational_llm("rewrite", 0.8)


def get_adaptive_llm(difficulty_level: str) -> BaseChatModel:
    """
    Get LLM adapted to user's difficulty level.

    Args:
        difficulty_level: "beginner", "intermediate", or "advanced"

    Returns:
        LLM with appropriate temperature
    """
    # Beginners need more varied examples (higher temp)
    # Advanced users need precise technical info (lower temp)
    temps = {
        "beginner": 0.8,
        "intermediate": 0.7,
        "advanced": 0.6
    }

    temp = temps.get(difficulty_level, 0.7)
    logger.debug(f"Adaptive educational LLM for {difficulty_level} level (temp={temp})")

    return get_base_llm(temperature=temp)


# ============================================================================
# PRICING AGENT LLMs
# ============================================================================

def get_pricing_llm(
    task: Literal["extraction", "validation", "decomposition", "planning", "narration"] = "extraction",
    temperature: Optional[float] = None
) -> BaseChatModel:
    """
    Get LLM configured for pricing agent tasks.

    Pricing agent needs low temperature for deterministic, accurate parameter extraction.

    Task-specific defaults:
    - extraction: 0.0 (fully deterministic parameter extraction)
    - validation: 0.0 (consistent validation logic)
    - decomposition: 0.1 (minimal creativity for feature detection)
    - planning: 0.0 (deterministic execution planning)
    - narration: 0.3 (slightly creative result presentation)

    Args:
        task: Pricing task type
        temperature: Override temperature, or None for task default

    Returns:
        Configured LLM instance
    """
    # Task-specific temperature defaults
    defaults = {
        "extraction": 0.0,
        "validation": 0.0,
        "decomposition": 0.1,
        "planning": 0.0,
        "narration": 0.3
    }

    temp = temperature if temperature is not None else defaults[task]

    logger.debug(f"Pricing LLM for '{task}' task (temp={temp})")
    return get_base_llm(temperature=temp)


def get_parameter_extractor_llm() -> BaseChatModel:
    """
    LLM for extracting option parameters from user queries.

    Zero temperature (0.0) for deterministic, accurate extraction.
    """
    return get_pricing_llm("extraction", 0.0)


def get_validator_llm() -> BaseChatModel:
    """
    LLM for validating extracted parameters.

    Zero temperature (0.0) for consistent validation logic.
    """
    return get_pricing_llm("validation", 0.0)


def get_decomposer_llm() -> BaseChatModel:
    """
    LLM for decomposing option strategies into components.

    Very low temperature (0.1) for accurate feature detection
    with minimal variation.
    """
    return get_pricing_llm("decomposition", 0.1)


def get_planner_llm() -> BaseChatModel:
    """
    LLM for creating execution plans.

    Zero temperature (0.0) for deterministic, reproducible plans.
    """
    return get_pricing_llm("planning", 0.0)


def get_narrator_llm() -> BaseChatModel:
    """
    LLM for narrating pricing results in natural language.

    Low-medium temperature (0.3) for clear, slightly varied
    result presentation.
    """
    return get_pricing_llm("narration", 0.3)


# ============================================================================
# ORCHESTRATOR LLMs
# ============================================================================

def get_orchestrator_llm(
    task: Literal["classification", "routing", "merging"] = "classification",
    temperature: Optional[float] = None
) -> BaseChatModel:
    """
    Get LLM for orchestrator tasks.

    Orchestrator coordinates between agents and needs consistent classification.

    Task-specific defaults:
    - classification: 0.3 (consistent intent detection)
    - routing: 0.0 (deterministic routing decisions)
    - merging: 0.2 (consistent result combination)

    Args:
        task: Orchestrator task type
        temperature: Override temperature, or None for task default

    Returns:
        Configured LLM instance
    """
    defaults = {
        "classification": 0.3,
        "routing": 0.0,
        "merging": 0.2
    }

    temp = temperature if temperature is not None else defaults[task]

    logger.debug(f"Orchestrator LLM for '{task}' task (temp={temp})")
    return get_base_llm(temperature=temp)


def get_intent_classifier_llm() -> BaseChatModel:
    """
    LLM for classifying user intent (educational vs pricing).

    Medium-low temperature (0.3) for consistent classification
    with some flexibility for edge cases.
    """
    return get_orchestrator_llm("classification", 0.3)


def get_router_llm() -> BaseChatModel:
    """
    LLM for routing decisions between agents.

    Zero temperature (0.0) for deterministic routing.
    """
    return get_orchestrator_llm("routing", 0.0)


# ============================================================================
# AGENT-AWARE LLM SELECTOR
# ============================================================================

def get_llm_for_agent(
    agent_type: AgentType,
    task: str = "default",
    temperature: Optional[float] = None
) -> BaseChatModel:
    """
    Get appropriate LLM based on agent type and task.

    This is the main factory function that selects the right LLM
    configuration based on agent context.

    Args:
        agent_type: Agent type ("educational", "pricing", or "unified")
        task: Task-specific identifier
        temperature: Optional temperature override

    Returns:
        Configured LLM instance

    Examples:
        >>> get_llm_for_agent("educational", "explanation")
        # Returns LLM with temp=0.7

        >>> get_llm_for_agent("pricing", "extraction")
        # Returns LLM with temp=0.0

        >>> get_llm_for_agent("unified", "classification")
        # Returns LLM with temp=0.3
    """
    if agent_type == "educational":
        # Educational tasks
        if task in ["explanation", "generate", "default"]:
            return get_explanation_generator_llm()
        elif task in ["assessment", "critique", "evaluate"]:
            return get_explanation_critic_llm()
        elif task in ["verification", "questions"]:
            return get_verification_llm()
        elif task in ["rewrite", "improve"]:
            return get_rewriter_llm()
        else:
            logger.warning(f"Unknown educational task '{task}', using default")
            return get_educational_llm("explanation", temperature)

    elif agent_type == "pricing":
        # Pricing tasks
        if task in ["extraction", "extract", "default"]:
            return get_parameter_extractor_llm()
        elif task in ["validation", "validate"]:
            return get_validator_llm()
        elif task in ["decomposition", "decompose"]:
            return get_decomposer_llm()
        elif task in ["planning", "plan"]:
            return get_planner_llm()
        elif task in ["narration", "narrate", "results"]:
            return get_narrator_llm()
        else:
            logger.warning(f"Unknown pricing task '{task}', using default")
            return get_pricing_llm("extraction", temperature)

    elif agent_type == "unified":
        # Unified/orchestrator tasks
        if task in ["classification", "classify", "default"]:
            return get_intent_classifier_llm()
        elif task in ["routing", "route"]:
            return get_router_llm()
        else:
            logger.warning(f"Unknown unified task '{task}', using default")
            return get_orchestrator_llm("classification", temperature)

    else:
        logger.error(f"Unknown agent type '{agent_type}', using default LLM")
        return get_base_llm(temperature=temperature or 0.3)


# ============================================================================
# TEMPERATURE COMPARISON TABLE
# ============================================================================

def get_temperature_table() -> str:
    """
    Get formatted table showing temperature settings by agent and task.

    Returns:
        Formatted string table
    """
    table = """
Agent Temperature Configuration
================================

EDUCATIONAL AGENT:
  Task                Temperature    Rationale
  ─────────────────────────────────────────────────────────────
  Explanation         0.7            Creative, engaging, varied
  Assessment          0.3            Consistent evaluation
  Verification        0.5            Balanced question variety
  Rewrite             0.8            Creative improvements

  Adaptive by Level:
    Beginner          0.8            More varied examples
    Intermediate      0.7            Balanced approach
    Advanced          0.6            Precise technical info

PRICING AGENT:
  Task                Temperature    Rationale
  ─────────────────────────────────────────────────────────────
  Extraction          0.0            Fully deterministic
  Validation          0.0            Consistent logic
  Decomposition       0.1            Minimal variation
  Planning            0.0            Reproducible plans
  Narration           0.3            Slightly creative

ORCHESTRATOR:
  Task                Temperature    Rationale
  ─────────────────────────────────────────────────────────────
  Classification      0.3            Consistent with flexibility
  Routing             0.0            Deterministic decisions
  Merging             0.2            Consistent combination

================================
"""
    return table


# ============================================================================
# LOGGING & MONITORING
# ============================================================================

def log_llm_usage(
    agent_type: AgentType,
    task: str,
    temperature: float,
    model_name: str
):
    """
    Log LLM usage for monitoring and debugging.

    Args:
        agent_type: Agent using the LLM
        task: Task being performed
        temperature: Temperature setting
        model_name: Model identifier
    """
    logger.info(
        f"[{agent_type.upper()}] LLM: {model_name} "
        f"(task={task}, temp={temperature:.1f})"
    )


if __name__ == "__main__":
    # Print temperature configuration table
    print(get_temperature_table())
