"""Enums for graph routing decisions."""

from enum import Enum


class ResponseType(str, Enum):
    """Response types for classification routing."""

    CAN_PRICE = "can_price"
    EXPLAIN_CONCEPT = "explain_concept"
    RECOGNIZE_BUT_REFUSE = "recognize_but_refuse"
    CLARIFY_PARAMETERS = "clarify_parameters"
    CLARIFY_OPTION = "clarify_option"
    CLARIFY_ASSET = "clarify_asset"
    OFF_TOPIC = "off_topic"


class AssetType(str, Enum):
    """Asset types for classification."""

    STOCK = "stock"
    INDEX = "index"
    ETF = "etf"
    COMMODITY = "commodity"
    FOREX = "forex"
    CRYPTO = "crypto"
    UNKNOWN = "unknown"


class OptionType(str, Enum):
    """Option types for classification."""

    CALL = "call"
    PUT = "put"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    SPREAD = "spread"
    BUTTERFLY = "butterfly"
    UNKNOWN = "unknown"


class StrategyType(str, Enum):
    """Strategy types for execution."""

    SINGLE = "single"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    SPREAD = "spread"
    BUTTERFLY = "butterfly"


class ProductType(str, Enum):
    """Product types for exotic options."""

    VANILLA = "vanilla"
    ASIAN = "asian"
    BARRIER = "barrier"
    LOOKBACK = "lookback"
    RAINBOW = "rainbow"
    VARIANCE_SWAP = "variance_swap"
    COMPOUND = "compound"
    DIGITAL = "digital"
    BINARY = "binary"
    AMERICAN = "american"
    UNKNOWN = "unknown"


class GraphNode(str, Enum):
    """Graph node names for routing."""

    # Classification nodes
    CLASSIFY_INTENT = "classify"
    AUGMENT_WITH_CONTEXT = "augment_with_context"
    WEB_SEARCH = "web_search"
    CLASSIFY_ASSET_TYPE = "classify_asset_type"
    CLASSIFY_OPTION_TYPE = "classify_option_type"
    DETERMINE_ACTION = "determine_action"

    # Response handler nodes
    RECOGNIZE_BUT_REFUSE = "recognize_but_refuse"
    CLARIFY_PARAMETERS = "clarify_parameters"
    CLARIFY_ASSET = "clarify_asset"
    CLARIFY_OPTION = "clarify_option"
    OFF_TOPIC = "off_topic"
    EXPLAIN_CONCEPT = "explain_concept"
    VALIDATION_FAILED = "validation_failed"

    # Execution nodes
    HUMAN_APPROVAL = "human_approval"
    DECOMPOSE = "decompose"
    CREATE_PLAN = "create_plan"
    VALIDATE = "validate"
    EXECUTE = "execute"
    NARRATE = "narrate"
    AGGREGATE = "aggregate"
    PRICING_COMPLETE = "pricing_complete"


class TaskType(str, Enum):
    """Task types for parallel execution."""

    MARKET_DATA = "market_data"
    VOLATILITY = "volatility"
    RISK_FREE_RATE = "risk_free_rate"
    PRICING = "pricing"
    SUM = "sum"


# Routing constants
OPTION_RELATED_ROUTE = "augment_with_context"
OFF_TOPIC_ROUTE = "off_topic"

# Response type to node mapping
RESPONSE_TYPE_TO_NODE: dict[ResponseType, str] = {
    ResponseType.CAN_PRICE: GraphNode.HUMAN_APPROVAL.value,
    ResponseType.EXPLAIN_CONCEPT: GraphNode.EXPLAIN_CONCEPT.value,
    ResponseType.RECOGNIZE_BUT_REFUSE: GraphNode.RECOGNIZE_BUT_REFUSE.value,
    ResponseType.CLARIFY_PARAMETERS: GraphNode.CLARIFY_PARAMETERS.value,
    ResponseType.CLARIFY_OPTION: GraphNode.CLARIFY_OPTION.value,
    ResponseType.CLARIFY_ASSET: GraphNode.CLARIFY_ASSET.value,
}
