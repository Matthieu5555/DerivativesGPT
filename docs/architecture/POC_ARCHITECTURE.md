# 🏗️ Agent Separation POC - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              AGENT DETECTION (POC)                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ detect_agent_type(query)                                 │  │
│  │                                                          │  │
│  │ • Keyword Pattern Matching                              │  │
│  │ • Educational vs Pricing Score                          │  │
│  │ • Confidence Calculation                                │  │
│  │ • Reasoning Generation                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
                ▼            ▼            ▼
         🎓 Educational  💰 Pricing   🤖 Unified
         Agent Type     Agent Type   Agent Type
                │            │            │
                └────────────┼────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AGENT MONITOR                                 │
│                                                                 │
│  Tracks:                                                        │
│  • Node executions                                              │
│  • Field read/write operations                                  │
│  • Access violations                                            │
│  • Session statistics                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FIELD ACCESS TRACKER                           │
│                                                                 │
│  ┌──────────────────┬──────────────────┬─────────────────────┐ │
│  │  Shared Fields   │ Educational      │ Pricing Fields      │ │
│  │  (All Agents)    │ Fields           │                     │ │
│  ├──────────────────┼──────────────────┼─────────────────────┤ │
│  │ • messages       │ • explanation_   │ • spot_price        │ │
│  │ • thread_id      │   text           │ • strike_price      │ │
│  │ • user_id        │ • user_          │ • execution_plan    │ │
│  │ • is_option_     │   understanding_ │ • execution_        │ │
│  │   related        │   score          │   results           │ │
│  │ • response_type  │ • verification_  │ • option_price      │ │
│  │ • ticker         │   questions      │ • validation_       │ │
│  │                  │ • rag_sources    │   errors            │ │
│  └──────────────────┴──────────────────┴─────────────────────┘ │
│                                                                 │
│  Validation:                                                    │
│  ✅ Educational agent reading explanation_text → ALLOWED        │
│  ❌ Educational agent writing spot_price → VIOLATION            │
│  ✅ Pricing agent writing execution_plan → ALLOWED              │
│  ❌ Pricing agent reading user_understanding_score → VIOLATION  │
└─────────────────────────────────────────────────────────────────┘
```

## Current Flow (With POC)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User sends message: "What is delta hedging?"                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. classify_intent_monitored                                    │
│    ├─ Detect agent: EDUCATIONAL (confidence: 70%)              │
│    ├─ Run original classification                              │
│    ├─ Track field accesses                                     │
│    └─ Log routing decision                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Graph continues with existing nodes                          │
│    (augment_with_context → classify_asset_type → ...)          │
│                                                                 │
│    Agent Monitor wraps each node:                              │
│    ├─ log_node_entry()                                         │
│    ├─ track read_field("messages")                             │
│    ├─ track write_field("explanation_text")                    │
│    └─ log_node_exit()                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Session Report Generated                                     │
│                                                                 │
│    Agent: EDUCATIONAL                                           │
│    Confidence: 70%                                              │
│    Nodes Executed: 5                                            │
│    Field Accesses: 12 (0 violations)                            │
└─────────────────────────────────────────────────────────────────┘
```

## Future Architecture (Full Implementation)

```
                        ┌─────────────┐
                        │   USER      │
                        └──────┬──────┘
                               │
                               ▼
                    ┌────────────────────┐
                    │   ORCHESTRATOR     │
                    │   AGENT            │
                    │                    │
                    │ • Intent Detection │
                    │ • Agent Selection  │
                    │ • Result Merging   │
                    └──────┬─────┬───────┘
                           │     │
                ┌──────────┘     └──────────┐
                │                           │
                ▼                           ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │  EDUCATIONAL AGENT    │   │   PRICING AGENT       │
    │                       │   │                       │
    │  Graph:               │   │  Graph:               │
    │  ├─ RAG Retrieval     │   │  ├─ Extract Params    │
    │  ├─ Generate Explain  │   │  ├─ Validate Inputs   │
    │  ├─ Critique Quality  │   │  ├─ Decompose         │
    │  ├─ Rewrite if Needed │   │  ├─ Create Plan       │
    │  ├─ Verify Understand │   │  ├─ Execute Parallel  │
    │  └─ Adapt Difficulty  │   │  └─ Narrate Results   │
    │                       │   │                       │
    │  State:               │   │  State:               │
    │  ├─ explanation_text  │   │  ├─ spot_price        │
    │  ├─ quality_score     │   │  ├─ execution_plan    │
    │  ├─ user_level        │   │  ├─ option_price      │
    │  └─ rag_sources       │   │  └─ validation_errors │
    │                       │   │                       │
    │  LLM: GPT-4           │   │  LLM: GPT-4           │
    │  Temp: 0.7            │   │  Temp: 0.0            │
    │                       │   │                       │
    │  Checkpoint:          │   │  Checkpoint:          │
    │  session.educational  │   │  session.pricing      │
    └───────────────────────┘   └───────────────────────┘
                │                           │
                └──────────┬────────────────┘
                           │
                           ▼
                    ┌────────────────┐
                    │  SHARED        │
                    │  SERVICES      │
                    │                │
                    │  • RAG         │
                    │  • LLM Pool    │
                    │  • Market Data │
                    │  • Checkpoints │
                    └────────────────┘
```

## Component Responsibilities

### Agent Detection
- **Input**: User query string
- **Output**: `AgentDetectionResult` (type, confidence, reasoning)
- **Responsibility**: Lightweight classification to route queries
- **Method**: Regex keyword pattern matching

### Field Access Tracker
- **Input**: Field name, agent type, operation (read/write)
- **Output**: Boolean (allowed/denied), logs violations
- **Responsibility**: Enforce agent boundaries, track access patterns
- **Method**: Whitelist-based validation against predefined field sets

### Agent Monitor
- **Input**: State object, node name, session ID
- **Output**: Wrapped read/write operations, session reports
- **Responsibility**: Observability layer for agent behavior
- **Method**: Decorator pattern wrapping state access

### Monitored Classification Node
- **Input**: `OptionPricingState`
- **Output**: Classification result + agent metadata
- **Responsibility**: Entry point for agent detection
- **Method**: Wrapper around existing `classify_intent`

## Data Flow

```
User Query
    │
    ▼
Agent Detection
    │
    ├─ Educational Keywords → 🎓 Educational Agent
    ├─ Pricing Keywords     → 💰 Pricing Agent
    └─ Unclear/Mixed        → 🤖 Unified Agent
    │
    ▼
State Access (monitored)
    │
    ├─ Read Field
    │   ├─ Check if allowed for agent type
    │   ├─ Log access
    │   └─ Return value or default
    │
    └─ Write Field
        ├─ Check if allowed for agent type
        ├─ Log access (warn if violation)
        └─ Write value or skip
    │
    ▼
Session Tracking
    │
    ├─ Track node executions
    ├─ Track field accesses
    ├─ Count violations
    └─ Generate report on demand
```

## Violation Detection Example

```python
# Educational agent tries to write pricing field
monitor = AgentMonitor(state, "educational_node", "session_123")
monitor.current_agent  # "educational"

# This is ALLOWED (shared field)
monitor.read_field("messages", state.messages)  # ✅

# This is ALLOWED (educational field)
monitor.write_field("explanation_text", "...")  # ✅

# This is a VIOLATION (pricing field)
monitor.write_field("spot_price", 150.0)  # ❌
# Logs: "⚠️  [EDUCATIONAL] Unauthorized write to 'spot_price'"
```

## Integration Points

### Current (POC)
1. **Entry Point**: `classify_intent_monitored` wraps `classify_intent`
2. **Activation**: Environment variable `ENABLE_AGENT_MONITORING_POC=true`
3. **Logging**: Standard Python logging with agent context
4. **Reports**: On-demand via `get_session_report(session_id)`

### Future (Full Implementation)
1. **Entry Point**: New orchestrator graph
2. **State Wrapper**: All state access goes through `AgentStateWrapper`
3. **Checkpointing**: Agent-specific thread IDs and persistence
4. **Sub-graphs**: Separate educational and pricing graphs
5. **Communication**: Message passing between agents via orchestrator

## Performance Considerations

### POC Overhead
- **Detection**: ~0.1ms (regex matching)
- **Tracking**: ~0.01ms per field access (dict lookup + logging)
- **Total**: <1ms per node execution

### Full Implementation Overhead
- **State wrapper**: ~0.1ms per field access (validation + copying)
- **Agent routing**: ~50-100ms (sub-graph invocation)
- **Total**: <5% overhead expected

## Testing Strategy

### POC Testing (Current)
- ✅ Unit tests for detection accuracy
- ✅ Integration tests for field tracking
- ✅ Standalone validation script
- ✅ Manual testing with sample queries

### Full Implementation Testing (Future)
- [ ] End-to-end agent routing tests
- [ ] State isolation tests
- [ ] Checkpoint migration tests
- [ ] Performance benchmarks
- [ ] User acceptance testing

---

*This POC provides the foundation for full agent separation while maintaining backward compatibility and providing clear observability into agent behavior.*
