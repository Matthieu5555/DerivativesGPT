"""
LLM-as-a-Judge Evaluation Prompts

These prompts evaluate whether the system's response matches the expected graph state.
The key criterion: Does the response type align with what the graph should produce?

GRAPH STATES AND EXPECTED RESPONSES:
- pricing_complete: Should provide calculated price with parameters
- generate_explanation: Should provide educational content with RAG sources
- off_topic: Should politely refuse non-options queries
- recognize_but_refuse: Should explain why exotic option can't be priced + list what CAN be priced
- clarify_parameters/clarify_asset/clarify_option: Should ask clarifying questions
"""

STATE_ALIGNMENT_PROMPT = """You are evaluating whether the system response matches the expected graph state.

Query: {query}
Response: {response}
Expected Graph State: {expected_state}

EVALUATION CRITERIA BY STATE:

1. **pricing_complete**: Response should contain:
   - Calculated option price (numerical value)
   - Extracted parameters (ticker, strike, expiry, option type)
   - Pricing method used (Black-Scholes, Bjerksund-Stensland, etc.)
   - NO educational explanations or refusals

2. **generate_explanation**: Response should contain:
   - Educational explanation of the concept
   - RAG-augmented content with source citations
   - Clear definition and examples
   - NO price calculations

3. **off_topic**: Response should contain:
   - Polite refusal
   - Explanation that query is not options-related
   - NO attempt to answer the off-topic question
   - NO price calculations

4. **recognize_but_refuse**: Response should contain:
   - Recognition of exotic option type
   - Explanation why it cannot be priced
   - List of option types that CAN be priced
   - NO price calculation

5. **clarify_parameters/clarify_asset/clarify_option**: Response should contain:
   - Specific clarifying questions
   - Identification of missing information
   - NO price calculation until parameters provided

SCORING RULES (BE DIRECT AND UNAMBIGUOUS):
- 5: Response FULLY matches expected state. All required elements present, no contradictions.
      For pricing_complete: All parameters extracted AND price calculated = 5
      For generate_explanation: Educational content with sources = 5
      For off_topic/refuse: Polite refusal without attempting task = 5
- 4: Response matches expected state with minor formatting/presentation issues only
- 3: Response attempts correct state but missing 1-2 key elements
- 2: Response partially matches but has major gaps or contradictions
- 1: Response completely wrong - attempted different state entirely

CRITICAL: If the response accomplishes what the expected state requires, the score is 5.
Do not reduce scores for stylistic preferences. Either it meets the state or it doesn't.

Return ONLY this JSON (no markdown, no extra text):
{{"score": <1-5>, "reasoning": "<explanation of alignment or misalignment>"}}"""

CORRECTNESS_PROMPT = """You are an expert options pricing analyst evaluating correctness.

Query: {query}
Response: {response}

Evaluate correctness (1-5):
- 5: Price accurate, correct model, all parameters extracted correctly
- 4: Mostly accurate with minor parameter issues
- 3: Moderate errors in calculation or parameters
- 2: Major errors (wrong model, wrong parameters, or >10% price error)
- 1: Completely wrong

Note: Only evaluate if response contains a price calculation. Return N/A if educational/off-topic.

Return ONLY this JSON (no markdown, no extra text):
{{"score": <1-5 or "N/A">, "reasoning": "<explanation>"}}"""

COMPLETENESS_PROMPT = """You are an expert evaluating parameter extraction.

Query: {query}
Response: {response}

Evaluate completeness (1-5):
- 5: All parameters extracted (ticker, strike, expiry, type)
- 4: All extracted with minor clarification
- 3: Most extracted, some clarification needed
- 2: Missing critical parameters
- 1: Failed to extract

Note: Only evaluate for pricing queries. Return N/A if educational/off-topic.

Return ONLY this JSON (no markdown, no extra text):
{{"score": <1-5 or "N/A">, "reasoning": "<explanation>"}}"""

CLARITY_PROMPT = """You are an expert evaluating response clarity.

Query: {query}
Response: {response}

Evaluate clarity (1-5):
- 5: Exceptionally clear, well-structured, easy to understand
- 4: Clear and understandable
- 3: Somewhat clear but could be better organized
- 2: Confusing structure or unclear language
- 1: Incomprehensible

Return ONLY this JSON (no markdown, no extra text):
{{"score": <1-5>, "reasoning": "<explanation>"}}"""

RAG_QUALITY_PROMPT = """You are an expert evaluating RAG source quality.

Query: {query}
Response: {response}

Evaluate RAG quality (1-5):
- 5: Highly relevant sources, accurately cited, adds significant value
- 4: Relevant sources, properly cited
- 3: Sources present but marginally relevant
- 2: Sources not relevant or poorly used
- 1: No sources or completely irrelevant

Note: Only evaluate for educational queries. Return N/A if pricing/off-topic.

Return ONLY this JSON (no markdown, no extra text):
{{"score": <1-5 or "N/A">, "reasoning": "<explanation>"}}"""
