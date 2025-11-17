"""
Base Agent State
=================
Shared state fields used by all agents (educational, pricing).

Contains:
- Conversation messages
- Initial classification (option-related check)
- Agent context (current agent, routing info)
- RAG and web search results
- Common metadata
"""

from typing import Annotated, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class BaseAgentState(BaseModel):
    """
    Base state shared by all agents.

    This contains fields that are common across educational and pricing agents:
    - Conversation messages
    - Classification results
    - Agent routing information
    - RAG/web search results
    - Common metadata
    """

    # === CONVERSATION ===
    messages: Annotated[list[BaseMessage], add_messages]

    # === INITIAL CLASSIFICATION (classify_intent node) ===
    is_option_related: bool | None = Field(
        default=None,
        description="Binary classification: option-related or off-topic"
    )
    initial_reasoning: str | None = Field(
        default=None,
        description="Initial classification reasoning"
    )
    extracted_ticker: str | None = Field(
        default=None,
        description="Ticker extracted by classifier"
    )

    # === DETAILED CLASSIFICATION (post-RAG) ===
    can_price: bool | None = Field(
        default=None,
        description="Whether request is priceable"
    )
    detected_product_type: str | None = Field(
        default=None,
        description="Initially detected product type from classification (e.g., 'european_call', 'barrier_option')"
    )
    features_detected: list[str] | None = Field(
        default=None,
        description="List of detected features (e.g., ['path_dependent', 'early_exercise'])"
    )
    asset_class: str | None = Field(
        default=None,
        description="Asset class (e.g., 'equity', 'fx', 'commodity')"
    )
    response_type: Literal["can_price", "recognize_but_refuse", "clarify", "off_topic", "explain_concept"] | None = Field(
        default=None,
        description="Type of response to generate"
    )
    reasoning: str | None = Field(
        default=None,
        description="Classification reasoning"
    )

    # === POST-AUGMENTATION CLASSIFICATION ===
    asset_type_classified: str | None = Field(
        default=None,
        description="Classified asset type: equity, fx, commodity, interest_rate, credit, unknown"
    )
    option_type_classified: str | None = Field(
        default=None,
        description="Classified option type: vanilla_call, vanilla_put, asian, barrier, american, straddle, unknown"
    )
    clarification_context: str | None = Field(
        default=None,
        description="What needs clarification: asset_type, option_type, or parameters"
    )

    # === RAG CONTEXT (shared by both agents) ===
    rag_sources: list[dict] | None = Field(
        default=None,
        description="Retrieved sources: [{'text': str, 'book': str, 'page': int, 'score': float, 'chunk_id': str}]"
    )
    rag_query: str | None = Field(
        default=None,
        description="Query used for RAG retrieval"
    )
    reformulated_rag: str | None = Field(
        default=None,
        description="LLM-reformulated RAG content with irrelevant context removed"
    )

    # === WEB SEARCH CONTEXT (shared by both agents) ===
    web_search_results: list[dict] | None = Field(
        default=None,
        description="Web search results from Tavily"
    )
    web_search_query: str | None = Field(
        default=None,
        description="Query formulated for web search based on RAG gaps"
    )

    # === COMMON METADATA ===
    ticker: str | None = None  # Used by both agents for context
    spot_price: float | None = Field(
        default=None,
        description="Current spot price extracted from market data"
    )
    chart_generated: bool | None = Field(
        default=None,
        description="Whether chart was successfully generated for ticker"
    )
    is_evaluation_mode: bool = Field(
        default=False,
        description="Flag to indicate evaluation/testing mode (fail fast instead of asking for clarification)"
    )

    # === AGENT SEPARATION & ROUTING ===
    detected_agent_type: Literal["educational", "pricing", "unified"] | None = Field(
        default=None,
        description="Detected agent type from query classification"
    )
    agent_confidence: float | None = Field(
        default=None,
        description="Confidence score for agent detection (0.0 to 1.0)"
    )
    agent_reasoning: str | None = Field(
        default=None,
        description="Reasoning for agent type detection"
    )
    current_agent: str | None = Field(
        default=None,
        description="Currently active agent handling the request"
    )

    # === CONVERSATION CONTEXT ===
    last_agent: str | None = Field(
        default=None,
        description="Previous agent that handled the last message"
    )
    last_topic: str | None = Field(
        default=None,
        description="Topic of the previous conversation turn"
    )
    conversation_depth: int = Field(
        default=0,
        description="Number of exchanges in current topic thread"
    )
    is_follow_up: bool = Field(
        default=False,
        description="Whether current message is a follow-up"
    )

    # === EDUCATIONAL CONVERSATION STATE (for persistence) ===
    educational_context: dict | None = Field(
        default=None,
        description="Educational conversation state (topic, mode, follow-ups) - serialized for persistence"
    )

    # === LOOP PROTECTION (needed by both agents) ===
    extraction_attempts: int = Field(
        default=0,
        description="Number of parameter extraction attempts (prevent infinite loops)"
    )
    max_extraction_attempts: int = Field(
        default=3,
        description="Maximum parameter extraction retry attempts before failing"
    )
    clarification_attempts: int = Field(
        default=0,
        description="Number of clarification attempts (prevent infinite loops)"
    )
    max_clarification_attempts: int = Field(
        default=3,
        description="Maximum clarification attempts before failing gracefully"
    )
    extraction_successful: bool = Field(
        default=False,
        description="Whether parameter extraction was successful"
    )

    # === ORTHOGONAL PRODUCT CLASSIFICATION (for pricing routing) ===
    position: Literal["long", "short"] | None = Field(
        default="long",  # Default to long position (buying)
        description="Position: long (buy) or short (sell)"
    )

    product_type: str | None = Field(
        default=None,
        description=(
            "Full product type for pricing routing:\n"
            "Vanilla: 'vanilla_european_call', 'vanilla_european_put'\n"
            "American: 'american_call', 'american_put'\n"
            "Digital: 'digital_call', 'digital_put'\n"
            "Asian: 'geometric_asian_call', 'geometric_asian_put'\n"
            "Exotic: 'barrier_call', 'lookback_put', etc.\n"
            "This determines which pricing engine to use"
        )
    )

    # === BASIC PRICING FIELDS (needed for routing logic) ===
    strike_price: float | str | None = Field(
        default=None,
        description="Strike price for the option (can be number or percentage like '5% above')"
    )
    execution_plan: dict | None = Field(
        default=None,
        description="Execution plan for pricing tasks"
    )
    time_to_expiry_days: float | None = Field(
        default=None,
        description="Time to expiry in days"
    )
    volatility: float | None = Field(
        default=None,
        description="Implied volatility"
    )
    risk_free_rate: float | None = Field(
        default=None,
        description="Risk-free interest rate"
    )
    option_type: str | None = Field(
        default=None,
        description="DEPRECATED: Use product_type instead. Legacy field for call/put direction only"
    )
    strategy_type: str | None = Field(
        default=None,
        description="Multi-leg strategy structure: single, straddle, strangle, spread, iron_condor, butterfly"
    )
    multi_leg: bool | None = Field(
        default=None,
        description="Whether this is a multi-leg strategy"
    )

    model_config = {"arbitrary_types_allowed": True}  # Required for BaseMessage
