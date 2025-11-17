"""Chainlit web interface with token streaming and chart display."""

import chainlit as cl
# Use the multi-agent orchestrator instead of old single graph
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from derivatives_gpt_core.conversation_memory.checkpoint_manager import get_checkpointer
from derivatives_gpt_core.observability.langsmith_setup import configure_langsmith
from derivatives_gpt_core.observability.metrics import metrics_tracker
from derivatives_gpt_core.observability.feedback import create_feedback_entry, log_feedback_to_langsmith
from derivatives_gpt_core.utils import format_pricing_response
from derivatives_gpt_core.utils.charting import create_price_chart
from langchain_core.messages import HumanMessage
import logging

# LangChain version compatibility for astream_events
try:
    import langchain_core
    from packaging import version
    LANGCHAIN_VERSION = version.parse(langchain_core.__version__)
    USE_V2_EVENTS = LANGCHAIN_VERSION >= version.parse("0.2.0")
except Exception:
    # Fallback if version check fails
    USE_V2_EVENTS = True  # Assume modern version

logger = logging.getLogger(__name__)

# Configure once at startup
configure_langsmith()

# Graph initialization
graph = None


async def _get_graph():
    """Get or create multi-agent orchestrator graph singleton."""
    global graph
    if graph is None:
        try:
            # Use the multi-agent orchestrator graph for proper follow-up handling
            graph = await build_orchestrator_graph()
            logger.info("Multi-agent orchestrator graph initialized with follow-up detection")
        except ValueError as e:
            raise RuntimeError(
                f"Failed to initialize graph: {e}\n"
                "Please check your .env file and ensure API keys are set."
            ) from e
    return graph


@cl.set_starters
async def set_starters():
    """Set starter prompts that appear as clickable buttons."""
    return [
        cl.Starter(
            label="Message #1 - Vanilla European Call on Apple",
            message="Can you help me to price a 1-year european call on AAPL, strike 5% above current market price, time to expiry 3 months?",
        ),
        cl.Starter(
            label="Message #2 - Knock-Out Barrier Option (Exotic)",
            message="Price a down-and-out barrier call on TSLA with strike $250, barrier at $200, expiring in 6 months.",
        ),
        cl.Starter(
            label="Message #3 - Educational Question",
            message="What is delta and how does it affect option pricing?",
        ),
        cl.Starter(
            label="Message #4 - American Put on Microsoft",
            message="Price an American put option on MSFT with strike $400, expiring in 90 days.",
        )
    ]


async def _display_price_chart(ticker: str) -> None:
    """
    Display a dark mode price chart for the ticker (chart display).

    Edge cases handled:
    - Chart creation fails: Log error but don't crash
    - Invalid ticker: Log error but don't crash
    - yfinance rate limit: Catch and show friendly message

    Args:
        ticker: Stock ticker symbol
    """
    try:
        from derivatives_gpt_core.utils.charting import create_price_chart

        logger.info(f"Creating chart for {ticker}")

        chart, spot_price, _ = create_price_chart(
            ticker=ticker,
            lookback_days=252,
            include_volume=True,
            include_sma=True
        )

        if chart:
            await cl.Message(
                content="",
                elements=[
                    cl.Plotly(
                        name=f"{ticker}_price_history",
                        figure=chart,
                        display="inline"
                    )
                ]
            ).send()
        else:
            logger.warning(f"Chart creation returned None for {ticker}")

    except Exception as e:
        # Don't crash on chart errors - just log and continue
        logger.error(f"Chart display error for {ticker}: {str(e)}", exc_info=True)
        # Optionally show a subtle message to user
        await cl.Message(
            content=f"_Chart unavailable for {ticker}_"
        ).send()


@cl.on_chat_start
async def start() -> None:
    """Initialize chat session with persistent thread ID."""
    # Use Chainlit's session ID for persistence across page refreshes
    thread_id = cl.context.session.id
    cl.user_session.set("thread_id", thread_id)


@cl.action_callback("thumbs_up")
async def on_thumbs_up(action: cl.Action):
    """Handle thumbs up feedback."""
    try:
        run_id = cl.user_session.get("last_run_id")
        if run_id:
            feedback = create_feedback_entry(score=1, category="good")
            log_feedback_to_langsmith(run_id, feedback)
            await cl.Message(content="Thanks for your positive feedback!").send()
        else:
            logger.warning("No run_id available for feedback")
    except Exception as e:
        logger.error(f"Error logging thumbs up: {e}", exc_info=True)


@cl.action_callback("thumbs_down")
async def on_thumbs_down(action: cl.Action):
    """Handle thumbs down feedback - prompt for category."""
    try:
        run_id = cl.user_session.get("last_run_id")
        if not run_id:
            logger.warning("No run_id available for feedback")
            return

        # Ask for category
        res = await cl.AskActionMessage(
            content="What went wrong?",
            actions=[
                cl.Action(name="incorrect_price", payload={"value": "incorrect_price"}, label="Incorrect Price"),
                cl.Action(name="wrong_parameters", payload={"value": "wrong_parameters"}, label="Wrong Parameters"),
                cl.Action(name="slow_response", payload={"value": "slow_response"}, label="Slow Response"),
                cl.Action(name="other", payload={"value": "other"}, label="Other"),
            ],
        ).send()

        if res:
            category = res.get("value")
            feedback = create_feedback_entry(score=0, category=category)
            log_feedback_to_langsmith(run_id, feedback)
            await cl.Message(content=f"Thanks for your feedback: {category.replace('_', ' ').title()}").send()
    except Exception as e:
        logger.error(f"Error logging thumbs down: {e}", exc_info=True)


@cl.on_message
async def main(message: cl.Message) -> None:
    """
    Handle user messages with progressive narration and charts (streaming implementation).
    ENHANCED: Now maintains conversation context for follow-up detection.

    Flow:
    1. Create a streaming message container
    2. Stream narration tokens from narration node only
    3. All other nodes (classify, plan, execute, validate) are silent
    4. Display final chart if market data was fetched
    5. Preserve conversation context for follow-ups

    Edge cases handled:
    - Graph configuration error: Show error message
    - Event stream error: Catch and display gracefully
    - Missing ticker in state: Skip chart display
    - Chart creation error: Log but don't crash
    """
    # Get or initialize the graph
    try:
        current_graph = await _get_graph()
    except RuntimeError as e:
        await cl.Message(content=f"WARNING: Configuration Error: {str(e)}").send()
        return

    # Get thread ID for conversation memory
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}

    # Create a streaming message container
    msg = cl.Message(content="")
    await msg.send()

    try:
        # Track if any content was streamed and capture run_id for feedback
        content_streamed = False
        chart_displayed = False
        run_id = None

        # Build input with conversation context
        input_messages = [HumanMessage(content=message.content)]
        input_dict = {"messages": input_messages}

        # Use ainvoke instead of astream_events since orchestrator doesn't stream
        # The orchestrator returns complete messages from agents
        import asyncio

        # Invoke the orchestrator with checkpointer in config
        final_response = await current_graph.ainvoke(input_dict, config)

        # Extract and display the response with simulated streaming
        if final_response and final_response.get("messages"):
            messages = final_response["messages"]
            if messages:
                # Get the last AI message (response)
                for message_obj in reversed(messages):
                    if (hasattr(message_obj, "content") and
                        message_obj.content and
                        not isinstance(message_obj, HumanMessage)):

                        # Simulate token streaming by chunking the response
                        full_content = message_obj.content
                        logger.info(f"Streaming response: {len(full_content)} chars")

                        # Stream tokens in small chunks for visual effect
                        chunk_size = 3  # Characters per chunk
                        for i in range(0, len(full_content), chunk_size):
                            chunk = full_content[i:i + chunk_size]
                            msg.content += chunk
                            await msg.update()
                            await asyncio.sleep(0.01)  # Small delay for streaming effect

                        content_streamed = True
                        # Skip run_id extraction as it requires checkpointer
                        # run_id is only needed for feedback buttons (optional)
                        break

        # Store conversation context for next interaction
        if final_response:
            logger.debug(f"Conversation context saved: last_agent={final_response.get('last_agent')}, "
                        f"conversation_depth={final_response.get('conversation_depth')}")
        
        # Finalize the message
        await msg.update()

        # Feedback buttons disabled (requires checkpointer for run_id)
        # To enable feedback, configure a checkpointer in the orchestrator graph

        # Chart is now displayed by the narrator via tool call (no separate display logic needed)

    except Exception as e:
        # Catch any streaming errors gracefully
        logger.error(f"Streaming error: {str(e)}", exc_info=True)
        await cl.Message(
            content=f"WARNING: An error occurred while processing your request: {str(e)}"
        ).send()
