"""Explanation generation prompts - pure functions."""

from typing import Literal


def build_explanation_prompt(
    query: str,
    rag_content: list[dict],
    web_content: list[dict] | None,
    difficulty: Literal["beginner", "intermediate", "advanced"],
    conversation_mode: Literal["initial_explanation", "followup_conversation"],
    previous_attempts: int = 0,
) -> str:
    """
    Pure function: Build explanation generation prompt.

    Handles two modes:
    - initial_explanation: Full structured template (TL;DR → Formal Definition)
    - followup_conversation: Conversational clarification on specific points

    Args:
        query: User's question
        rag_content: Retrieved educational content from internal knowledge base
        web_content: Retrieved content from web search (Tavily)
        difficulty: User's knowledge level
        conversation_mode: Initial full explanation vs follow-up conversation
        previous_attempts: Number of previous explanation attempts

    Returns:
        Formatted prompt string
    """
    if conversation_mode == "initial_explanation":
        return _build_structured_explanation_prompt(
            query=query,
            rag_content=rag_content,
            web_content=web_content,
            difficulty=difficulty,
            previous_attempts=previous_attempts,
        )
    else:  # followup_conversation
        return _build_followup_prompt(
            query=query,
            rag_content=rag_content,
            web_content=web_content,
            difficulty=difficulty,
        )


def _build_structured_explanation_prompt(
    query: str,
    rag_content: list[dict],
    web_content: list[dict] | None,
    difficulty: str,
    previous_attempts: int,
) -> str:
    """
    Build prompt for initial structured explanation.

    Uses the comprehensive template: TL;DR → Origin → Metaphor → Example → Formal Definition
    """
    difficulty_instructions = {
        "beginner": """Use simple language, minimal jargon, strong analogies.
- Define ALL technical terms inline on first use
- Use everyday examples (parking lot, insurance, games)
- Break down formulas into plain English first
- Keep mathematical notation minimal""",
        "intermediate": """Balance technical accuracy with clarity.
- Use standard financial terminology with brief inline definitions
- Include mathematical intuition alongside formulas
- Provide realistic trading examples with actual numbers
- Assume basic understanding of stocks and derivatives""",
        "advanced": """Use precise mathematical terminology, assume domain knowledge.
- Use technical terms without definitions (delta, theta, IV rank)
- Include rigorous mathematical formulas with proper notation
- Reference academic concepts (Black-Scholes, no-arbitrage, martingales)
- Assume familiarity with quantitative finance and stochastic calculus""",
    }

    retry_context = ""
    if previous_attempts > 0:
        retry_context = f"""
IMPORTANT: This is attempt #{previous_attempts + 1}. Previous explanations were unclear.
Please improve by:
- Using DIFFERENT examples or analogies than before
- Breaking down concepts more step-by-step
- Adding more concrete numerical details
- Simplifying language while maintaining accuracy
"""

    formatted_rag = format_rag_content(rag_content) if rag_content else "No internal knowledge base content retrieved."
    formatted_web = format_web_content(web_content) if web_content else "No web search results available."

    prompt = f"""You are an expert financial educator explaining complex derivatives concepts with exceptional clarity.

USER QUESTION: {query}

DIFFICULTY LEVEL: {difficulty}
{difficulty_instructions[difficulty]}

RETRIEVED KNOWLEDGE BASE CONTENT:
{formatted_rag}

WEB SEARCH RESULTS:
{formatted_web}
{retry_context}

CRITICAL INSTRUCTIONS:
- Write in FLOWING PROSE with logical connectors between ideas, NOT bullet point lists
- Each section should be written as connected paragraphs that build upon each other
- Use transition phrases like "Furthermore," "This leads to," "Consequently," "Building on this,"
- ALWAYS provide inline definitions for technical terms on first use:
  - Example: "OTM (out-of-the-money - an option that would have zero payoff if exercised immediately)"
  - Example: "delta-neutral (a portfolio whose value won't change for small price movements)"
  - Example: "IV (implied volatility - the market's expectation of future price fluctuations)"
- CITE knowledge base content using inline quotes when relevant to your explanation:
  - Format: "...quoted text from source..." (Book Title, Ch. X)
  - Example: "...the strike price is the same as the current price..." (Exotic Options & Hybrids, Ch. 3)
  - Integrate quotes naturally into your sentences
  - You will ALSO list all sources with quotes at the end in a Sources section
- Make the text read like a cohesive educational article, not a disconnected outline
- For mathematical notation: Use PLAIN TEXT ONLY
  - Write "Delta" not "$\\Delta$"
  - Write "S_0" or "S0" not "$S_0$"
  - Use basic symbols: %, +, -, *, /, =
  - Example: "Delta = N(d1)" not "$$\\Delta = N(d_1)$$"

TASK:
Generate a comprehensive, pedagogically excellent explanation using this EXACT STRUCTURE:

## **TL;DR** (50-300 words)
- Core concept in one sentence
- Key mechanism/how it works
- Primary use case
- Critical outcome/risk summary

## [Concept Name]

### 1. Origin/Purpose (≤200 words)
- **Problem statement**: What market need/inefficiency existed
- **Prior approach**: What traders used before (with brief inline definition)
- **Innovation**: How this concept solved the limitation
- **Core thesis**: The fundamental bet/assumption in plain terms

### 2. Visual Metaphor (≤200 words)
- **Real-world analog**: Relatable situation mapping to the concept (insurance, parking, games, etc.)
- **Key parallels**:
  - Profit mechanism → everyday equivalent
  - Risk limits → everyday protection
  - Decision points → everyday choices
- **Boundary conditions**: Where the metaphor holds and where it breaks

### 3. Real Example (≤200 words)
- **Setup context**: Market conditions and rationale
- **Specific construction**: Exact strikes/prices/dates with realistic numbers
  - Each component with inline purpose (e.g., "bear call spread (betting price won't rise much)")
  - NO placeholders - use actual dollar amounts
- **Outcome scenarios**:
  - Best case with dollar amounts
  - Worst case with dollar amounts
  - Breakeven conditions
- **Why this over alternatives**: Brief comparison to simpler strategies

### 4. Formal Definition (flexible length for mathematical notation)
- **Position construction**:
  - List each leg with inline explanation of purpose
  - Strike price relationships (inequalities showing structure)
- **Individual components first**:
  - Payoff formula for each leg
  - How legs interact/offset
- **Combined mathematics**:
  - Full piecewise function using plain text notation
  - Symbol definitions immediately after introduction: S_T = stock price at expiry
  - Connection to simpler forms where applicable
- **Key metrics**:
  - Maximum profit (formula + condition)
  - Maximum loss (formula + explanation of min/max operators)
  - Breakeven points with derivations
  - Greeks if relevant (delta, theta, vega, gamma) with brief explanations
- **Usage conditions**: When to deploy vs avoid

**Sources:**
For each knowledge base source provided above, you MUST include a direct quote:
- "...actual quoted text from the source content..." (Book Name, Ch. X)
- "...actual quoted text from the source content..." (Book Name, Ch. X)

Rules:
- Quote 20-50 words of ACTUAL text from the content provided
- Use ellipsis (...) at start and end to show it's an excerpt
- Include the source attribution from "Source X:" in parentheses
- If multiple sources, include quotes from each
- If no sources provided, write: [No knowledge base sources were retrieved]

QUALITY CHECKS BEFORE FINALIZING:
✓ No undefined jargon in first three sections
✓ Metaphor accessible to someone outside finance
✓ Example uses realistic market parameters (real stock prices, actual dates)
✓ Math builds from simple to complex progressively
✓ Each symbol defined before/at first use
✓ Practical usage guidance included
✓ Risk clearly quantified, not just mentioned

CRITICAL FORMATTING RULES:
1. **Inline definitions**: ALL complex terms get parenthetical explanations on FIRST use
   - Example: "short straddle (selling both a call and put at the same strike price)"
2. **Progressive complexity**: Individual components → Combined structure → Full mathematical representation
3. **Mathematical notation**: Define before use, relate to familiar concepts, use plain text only
   - Example: "S_0 = current stock price" or "Think of the integral as a continuous sum"
4. **Practical anchors**: Use dollar amounts, percentage moves, explicit time horizons
5. **No placeholders**: "AAPL at $190" not "Stock at $X" or "Strike K"
6. **Risk emphasis**: Maximum loss in dollar terms with conditions that trigger it

Begin your explanation:"""

    return prompt


def _build_followup_prompt(
    query: str,
    rag_content: list[dict],
    web_content: list[dict] | None,
    difficulty: str,
) -> str:
    """
    Build prompt for conversational follow-up questions.

    More focused, conversational tone for clarifying specific points.
    """
    formatted_rag = format_rag_content(rag_content) if rag_content else "No additional context retrieved."
    formatted_web = format_web_content(web_content) if web_content else ""

    sources_section = ""
    if formatted_rag != "No additional context retrieved." or formatted_web:
        sources_section = f"""
ADDITIONAL CONTEXT (if helpful):
{formatted_rag}
{formatted_web}
"""

    prompt = f"""You are an expert derivatives educator having a conversation with a student over coffee.

STUDENT'S FOLLOW-UP QUESTION: {query}

DIFFICULTY LEVEL: {difficulty}
{sources_section}

###CRITICAL RULES - READ CAREFULLY###
This is a CONVERSATIONAL FOLLOW-UP, not a structured explanation. You MUST:

**FORMAT (ABSOLUTELY REQUIRED):**
1. NO sections (no "##", no "###")
2. NO bullet points
3. NO numbered lists
4. NO "TL;DR" or structured headings
5. Write 3-5 natural paragraphs flowing into each other
6. Like explaining to a smart colleague at lunch

**TONE & STYLE:**
- Start by connecting to what you just explained ("Great question - this builds directly on delta...")
- Conversational and engaging ("Think about it this way...")
- Use "you" and "we" liberally
- Relate to practical trading scenarios
- Keep it concise (3-5 paragraphs, ~800-1200 characters)

**CONTENT:**
- Connect new concept to previous discussion naturally
- Use concrete examples with real numbers if helpful
- Gently correct misconceptions if detected
- End with a question or thought-provoker to keep dialogue going

**FORBIDDEN:**
- ❌ NO "Origin/Purpose" sections
- ❌ NO "Visual Metaphor" sections
- ❌ NO "Formal Definition" sections
- ❌ NO structured templates AT ALL
- ❌ NO LaTeX math (use plain text: "Delta = dV/dS")
- ❌ NO emojis

###EXAMPLE CONVERSATIONAL STYLE###
"Great question! Now that you understand delta measures how the option price moves with the stock, gamma tells you how fast that delta itself is changing.

Think back to that AAPL $200 call we talked about. When AAPL was at $190, maybe delta was 0.30. But as AAPL rises to $195, delta doesn't stay stuck at 0.30 - it might jump to 0.50. Gamma quantifies exactly how much delta shifts for each $1 move in the stock.

This matters for hedging because if you sold that call and delta-hedged it, your hedge starts breaking down as soon as the stock moves. High gamma means delta changes rapidly, forcing you to rebalance often - which costs money in transaction fees and slippage.

Want to walk through how gamma behaves differently for ITM vs OTM options?"

Now respond conversationally to the student's question:"""

    return prompt


def format_rag_content(rag_content: list[dict]) -> str:
    """
    Pure function: Format RAG content for prompt inclusion.

    Args:
        rag_content: List of dicts with 'source' and 'content' keys

    Returns:
        Formatted string of RAG sources
    """
    if not rag_content:
        return "No retrieved content."

    formatted_chunks = []
    for i, item in enumerate(rag_content, 1):
        source = item.get("source", "Unknown source")
        content = item.get("content", "").strip()

        formatted_chunks.append(f"""
Source {i}: {source}
---
{content}
---
""")

    return "\n".join(formatted_chunks)


def format_web_content(web_content: list[dict] | None) -> str:
    """
    Pure function: Format web search results for prompt inclusion.

    Args:
        web_content: List of dicts with 'title', 'url', 'content' keys

    Returns:
        Formatted string of web sources
    """
    if not web_content:
        return ""

    formatted_results = []
    for i, result in enumerate(web_content, 1):
        title = result.get("title", "Unknown")
        url = result.get("url", "")
        content = result.get("content", "").strip()

        formatted_results.append(f"""
Web Source {i}: {title}
URL: {url}
---
{content}
---
""")

    return "\n".join(formatted_results)
