"""CLI entry point."""

from derivatives_gpt_core.agent_graph_definition import create_option_pricing_graph
from derivatives_gpt_core.observability.langsmith_setup import configure_langsmith
from derivatives_gpt_core.utils import format_pricing_response
from langchain_core.messages import HumanMessage
import uuid
import logging
import sys

# Configure logging for CLI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)  # Log to stderr to keep stdout clean for user interaction
    ]
)

logger = logging.getLogger(__name__)


def run_cli() -> None:
    """Run interactive CLI."""
    configure_langsmith()

    logger.info("Initializing agent...")
    print("Initializing agent...")  # Keep this print for user feedback
    graph = create_option_pricing_graph()

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"CLI started with thread_id: {thread_id}")
    print("Ready! Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("CLI interrupted by user")
            print("\nGoodbye!")
            break

        if user_input.lower() in ("quit", "exit"):
            logger.info("User requested exit")
            print("Goodbye!")
            break

        if not user_input:
            continue

        logger.info(f"Processing user input: {user_input[:50]}...")

        try:
            result = graph.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )

            response = format_pricing_response(result)
            print(f"Agent: {response}\n")
            logger.info("Response generated successfully")

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            print(f"Error: {e}\n")


if __name__ == "__main__":
    run_cli()
