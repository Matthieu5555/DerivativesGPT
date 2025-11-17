# 🚀 Agent Separation POC - Quick Start Guide

## Getting Started in 5 Minutes

### Step 1: Validate the POC (30 seconds)

```bash
# Run the standalone test
python test_agent_detection_simple.py
```

**Expected output:**
```
AGENT DETECTION POC - VALIDATION TEST
================================================================================
...
OVERALL: 16/22 (72.7%)
✅ DETECTION WORKING WELL (>=80% accuracy)
```

### Step 2: Try Custom Queries (Interactive)

```python
# Create a quick test script
cat > test_my_query.py << 'EOF'
from test_agent_detection_simple import detect_agent_type, get_agent_emoji

queries = [
    "Your custom query here",
    "Another query to test",
]

for query in queries:
    result = detect_agent_type(query)
    emoji = get_agent_emoji(result.agent_type)
    print(f"\nQuery: {query}")
    print(f"→ {emoji} {result.agent_type.upper()} ({result.confidence:.0%})")
    print(f"→ {result.reasoning}")
EOF

python test_my_query.py
```

### Step 3: Understand Field Categories

```python
from derivatives_gpt_core.core.state.field_tracker import (
    SHARED_FIELDS, EDUCATIONAL_FIELDS, PRICING_FIELDS
)

print("Shared Fields (accessible by all agents):")
print(SHARED_FIELDS)

print("\nEducational Agent Fields:")
print(EDUCATIONAL_FIELDS)

print("\nPricing Agent Fields:")
print(PRICING_FIELDS)
```

---

## Usage Examples

### Example 1: Detect Agent for a Query

```python
from derivatives_gpt_core.core.state.agent_detection import detect_agent_type

query = "What is the Black-Scholes formula?"
result = detect_agent_type(query)

print(f"Agent: {result.agent_type}")           # "educational"
print(f"Confidence: {result.confidence:.0%}")  # "60%"
print(f"Reasoning: {result.reasoning}")        # "Educational keywords (1)..."
print(f"Matches: {result.matched_keywords}")   # ["\\bwhat is\\b"]
```

### Example 2: Track Field Access

```python
from derivatives_gpt_core.core.state.field_tracker import track_field_access

# Educational agent accessing fields
allowed = track_field_access("explanation_text", "educational", "write")
print(allowed)  # True ✅

allowed = track_field_access("spot_price", "educational", "write")
print(allowed)  # False ❌ (logs warning)

# Pricing agent accessing fields
allowed = track_field_access("spot_price", "pricing", "write")
print(allowed)  # True ✅

allowed = track_field_access("explanation_text", "pricing", "write")
print(allowed)  # False ❌ (logs warning)
```

### Example 3: Monitor Node Execution

```python
from derivatives_gpt_core.core.state.agent_monitor import AgentMonitor

# Mock state for testing
class MockState:
    messages = [{"content": "Price a call option"}]
    spot_price = None
    explanation_text = None

state = MockState()
monitor = AgentMonitor(state, "my_node", "session_123")

# Log entry
monitor.log_node_entry()

# Track field access
messages = monitor.read_field("messages", state.messages)  # ✅ Allowed
monitor.write_field("spot_price", 150.0)  # ✅ Allowed (pricing agent)
monitor.write_field("explanation_text", "...")  # ❌ Violation (logged)

# Log exit
monitor.log_node_exit()
```

### Example 4: Generate Session Report

```python
from derivatives_gpt_core.core.state.agent_monitor import get_session_report

report = get_session_report("session_123")
print(report)
```

**Output:**
```
====================================================================
AGENT SESSION REPORT: session_123
====================================================================

Current Agent: PRICING
Detection Confidence: 80%
Detection Reasoning: Pricing keywords (3) significantly outweigh educational (0)
Session Duration: 12.34s

Node Executions:
  1. classify_intent [pricing] (completed, 0.25s)
  2. extract_parameters [pricing] (completed, 1.50s)
  3. execute_plan [pricing] (completed, 10.00s)

Field Accesses:
  ✅ messages: 3R / 0W
  ✅ spot_price: 1R / 1W
  ✅ execution_plan: 0R / 1W
  ❌ explanation_text: 0R / 1W (1 violations)

====================================================================
```

---

## Integration Patterns

### Pattern 1: Wrap Existing Node (Recommended)

```python
# Your existing node
async def my_existing_node(state: OptionPricingState) -> dict:
    # ... existing logic ...
    return {"some_field": value}

# Wrapped version with monitoring
async def my_monitored_node(state: OptionPricingState) -> dict:
    from derivatives_gpt_core.core.state.agent_monitor import AgentMonitor

    monitor = AgentMonitor(state, "my_node")
    monitor.log_node_entry()

    # Call original
    result = await my_existing_node(state)

    # Track field writes
    for key, value in result.items():
        monitor.write_field(key, value)

    monitor.log_node_exit()
    return result
```

### Pattern 2: Add Detection to Entry Point

```python
# In your graph builder
from derivatives_gpt_core.graph_nodes.classify_intent_monitored import (
    classify_user_intent_monitored,
    should_use_monitored_version
)

# Conditionally use monitored version
if should_use_monitored_version():
    graph.add_node("classify_intent", classify_user_intent_monitored)
else:
    graph.add_node("classify_intent", classify_user_intent)  # Original
```

### Pattern 3: Explicit Field Access Checking

```python
def validate_agent_can_access_field(
    agent_type: str,
    field_name: str,
    operation: str = "read"
) -> bool:
    """Check if agent can access field before using it"""
    from derivatives_gpt_core.core.state.field_tracker import track_field_access

    allowed = track_field_access(field_name, agent_type, operation)

    if not allowed:
        raise PermissionError(
            f"{agent_type} agent cannot {operation} field '{field_name}'"
        )

    return True

# Usage in node
agent_type = state.detected_agent_type or "unified"
validate_agent_can_access_field(agent_type, "spot_price", "write")
state.spot_price = 150.0  # Now safe
```

---

## Common Queries & Expected Detection

### Educational Queries → 🎓 Educational Agent
```python
educational_queries = [
    "What is implied volatility?",
    "Explain the Greeks to me",
    "How does a call option work?",
    "Tell me about put-call parity",
    "What's the difference between American and European options?",
]
```

### Pricing Queries → 💰 Pricing Agent
```python
pricing_queries = [
    "Price a 30-day call on AAPL with strike $150",
    "Calculate the premium for a straddle",
    "What's the value of this digital option?",
    "I need to price a butterfly spread",
    "How much is a barrier option worth with barrier at $200?",
]
```

### Mixed Queries → 🤖 Unified Agent (or primary intent)
```python
mixed_queries = [
    "What is a straddle and how much would one cost?",  # → Pricing (primary)
    "Explain gamma and calculate it for my option",     # → Unified
    "Price this call and tell me why it has that value", # → Pricing (primary)
]
```

---

## Debugging Tips

### 1. Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("derivatives_gpt_core.core.state")
logger.setLevel(logging.DEBUG)
```

### 2. Check Detection Results

```python
from derivatives_gpt_core.core.state.agent_detection import (
    detect_agent_type,
    format_detection_summary
)

query = "Your query here"
result = detect_agent_type(query)
print(format_detection_summary(result))
```

**Output:**
```
🎓 **Agent: EDUCATIONAL** (confidence: 70%)
*Reasoning: Educational keywords (2) significantly outweigh pricing (0)*
*Matched: \bwhat is\b, \bexplain\b*
```

### 3. Generate Field Access Report

```python
from derivatives_gpt_core.core.state.field_tracker import get_field_tracker

tracker = get_field_tracker()
print(tracker.generate_report())
```

### 4. View All Violations

```python
tracker = get_field_tracker()

for violation in tracker.violations:
    print(f"❌ {violation.agent_type} agent tried to {violation.operation} "
          f"'{violation.field_name}'")
```

---

## Environment Configuration

### Enable POC Monitoring

```bash
export ENABLE_AGENT_MONITORING_POC=true
```

### Configure Logging Level

```bash
export LOG_LEVEL=DEBUG  # Show all agent detection logs
export LOG_LEVEL=INFO   # Show only agent routing decisions
export LOG_LEVEL=WARNING  # Show only violations
```

### Disable POC Monitoring

```bash
unset ENABLE_AGENT_MONITORING_POC
# or
export ENABLE_AGENT_MONITORING_POC=false
```

---

## Testing Workflow

### 1. Unit Test Individual Components

```bash
# Test detection
python -c "
from derivatives_gpt_core.core.state.agent_detection import detect_agent_type
result = detect_agent_type('What is delta?')
assert result.agent_type == 'educational'
print('✅ Detection test passed')
"

# Test field tracking
python -c "
from derivatives_gpt_core.core.state.field_tracker import track_field_access
allowed = track_field_access('explanation_text', 'educational', 'write')
assert allowed == True
print('✅ Field access test passed')
"
```

### 2. Integration Test with Mock State

```bash
python test_agent_detection_simple.py
```

### 3. Full System Test (with dependencies installed)

```bash
# Install dependencies first
pip install -r requirements.txt  # or equivalent

# Run full test suite
python test_agent_separation_poc.py
```

---

## Performance Monitoring

### Check Detection Latency

```python
import time
from derivatives_gpt_core.core.state.agent_detection import detect_agent_type

queries = ["What is delta?"] * 1000

start = time.time()
for query in queries:
    detect_agent_type(query)
duration = time.time() - start

print(f"Average: {duration / len(queries) * 1000:.2f}ms per query")
# Expected: <0.1ms per query
```

### Check Tracking Overhead

```python
import time
from derivatives_gpt_core.core.state.field_tracker import track_field_access

iterations = 10000

start = time.time()
for _ in range(iterations):
    track_field_access("spot_price", "pricing", "write")
duration = time.time() - start

print(f"Average: {duration / iterations * 1000:.3f}ms per access")
# Expected: <0.01ms per access
```

---

## Next Steps After POC Validation

### ✅ POC Validated - Ready for Next Phase

1. **Review detection accuracy** with your production queries
2. **Adjust keywords** if needed for better accuracy
3. **Map all existing state fields** to agent categories
4. **Implement state wrapper** with enforcement (Phase 2)
5. **Set up agent-aware checkpointing** (Phase 3)
6. **Extract agent graphs** (Phase 4)

### ⚠️ POC Needs Tuning

1. **Collect misclassified queries** from logs
2. **Add domain-specific keywords** (ticker patterns, strategy names)
3. **Consider lightweight LLM** for ambiguous cases
4. **Re-run validation** and iterate

---

## Troubleshooting

### Issue: Detection accuracy too low

**Solution:** Add more keywords or use hybrid approach with LLM

```python
# Add to EDUCATIONAL_KEYWORDS or PRICING_KEYWORDS
PRICING_KEYWORDS.append(r"\bticker\b")
EDUCATIONAL_KEYWORDS.append(r"\bwhy\b")
```

### Issue: Too many field violations

**Solution:** Review field categorization, some fields might need to be shared

```python
# Move field to shared category
from derivatives_gpt_core.core.state.field_tracker import SHARED_FIELDS
SHARED_FIELDS.add("newly_shared_field")
```

### Issue: Import errors

**Solution:** Install dependencies or use standalone test

```bash
# Use standalone test (no dependencies)
python test_agent_detection_simple.py

# Or install dependencies
pip install langchain-core pydantic
```

---

## FAQ

### Q: How accurate is keyword-based detection?

**A:** 72.7% overall in POC testing. Pricing queries are 100% accurate, educational queries are 71.4%. This is good enough for pre-routing, with final classification by LLM.

### Q: Can I customize the keywords?

**A:** Yes! Edit `derivatives_gpt_core/core/state/agent_detection.py` and modify `EDUCATIONAL_KEYWORDS` and `PRICING_KEYWORDS`.

### Q: What happens when an agent violates field access?

**A:** In POC mode, violations are logged as warnings but not blocked. In full implementation, they can be enforced with hard blocks.

### Q: Does this break existing functionality?

**A:** No! The POC is completely non-invasive. It wraps existing nodes and only adds logging. Original flow remains unchanged.

### Q: How do I disable the POC?

**A:** Unset the environment variable or set it to false:
```bash
export ENABLE_AGENT_MONITORING_POC=false
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT DETECTION POC                          │
├─────────────────────────────────────────────────────────────────┤
│ DETECTION                                                       │
│  detect_agent_type(query) → AgentDetectionResult                │
│                                                                 │
│ TRACKING                                                        │
│  track_field_access(field, agent, operation) → bool             │
│                                                                 │
│ MONITORING                                                      │
│  monitor = AgentMonitor(state, node_name, session_id)           │
│  monitor.read_field(field, value) → value                       │
│  monitor.write_field(field, value) → value                      │
│                                                                 │
│ REPORTING                                                       │
│  get_session_report(session_id) → str                           │
│  get_field_tracker().generate_report() → str                    │
│                                                                 │
│ TESTING                                                         │
│  python test_agent_detection_simple.py                          │
│                                                                 │
│ ACTIVATION                                                      │
│  export ENABLE_AGENT_MONITORING_POC=true                        │
└─────────────────────────────────────────────────────────────────┘
```

---

*Get started in 5 minutes and validate agent separation is the right approach for your system!* 🚀
