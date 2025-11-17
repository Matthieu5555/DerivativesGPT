"""
Chainlit Streaming Callback Handler
=====================================
Handles streaming of LLM tokens to Chainlit UI for real-time response display.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID
import chainlit as cl
from langchain.callbacks.base import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
import logging

logger = logging.getLogger(__name__)


class ChainlitStreamingCallbackHandler(AsyncCallbackHandler):
    """
    Async callback handler that streams LLM tokens to Chainlit UI.

    This handler:
    - Creates a streaming message when LLM starts
    - Streams tokens as they're generated
    - Finalizes the message when complete
    - Handles errors gracefully
    """

    def __init__(self, author: str = "Assistant"):
        """
        Initialize the streaming callback handler.

        Args:
            author: The author name to display for the message
        """
        super().__init__()
        self.message: Optional[cl.Message] = None
        self.author = author
        self.token_buffer = ""

    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """
        Called when LLM starts generating.
        Creates a new streaming message in Chainlit.
        """
        # Create new message for streaming
        self.message = cl.Message(content="", author=self.author)
        await self.message.send()
        self.token_buffer = ""
        logger.debug(f"Started streaming message from {self.author}")

    async def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any
    ) -> None:
        """
        Called when a new token is generated.
        Streams the token to the UI.
        """
        if self.message:
            # Accumulate token
            self.token_buffer += token

            # Stream update to UI
            await self.message.stream_token(token)

    async def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """
        Called when LLM finishes generating.
        Finalizes the streaming message.
        """
        if self.message:
            # Update with final content
            await self.message.update()
            logger.debug(f"Finished streaming message from {self.author}")

            # Reset for next use
            self.message = None
            self.token_buffer = ""

    async def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        **kwargs: Any
    ) -> None:
        """
        Called when LLM encounters an error.
        Updates the message with error information.
        """
        if self.message:
            error_msg = f"\n\nError during generation: {str(error)}"
            await self.message.stream_token(error_msg)
            await self.message.update()

            # Reset
            self.message = None
            self.token_buffer = ""

        logger.error(f"LLM streaming error: {error}")


class AgentStreamingCallbackHandler(ChainlitStreamingCallbackHandler):
    """
    Extended streaming handler that's agent-aware.
    Shows which agent is responding in the UI.
    """

    def __init__(self, agent_type: str = "unified"):
        """
        Initialize agent-aware streaming handler.

        Args:
            agent_type: Type of agent (educational, pricing, unified)
        """
        # Set author based on agent type - NO EMOJIS
        author_map = {
            "educational": "Educational Agent",
            "pricing": "Pricing Agent",
            "unified": "Assistant"
        }
        author = author_map.get(agent_type, "Assistant")
        super().__init__(author=author)

        self.agent_type = agent_type
        # NO EMOJIS - User explicitly requested no emojis
        self.show_agent_badge = False

    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """
        Called when LLM starts generating.
        Creates a new streaming message WITHOUT agent indicator (no emojis).
        """
        # Create message WITHOUT agent indicator or emoji
        self.message = cl.Message(
            content="",
            author=self.author
            # NO elements with emojis or badges
        )
        await self.message.send()
        self.token_buffer = ""
        logger.debug(f"Started streaming from {self.agent_type} agent")


def get_streaming_callback(agent_type: Optional[str] = None) -> ChainlitStreamingCallbackHandler:
    """
    Factory function to get appropriate streaming callback handler.

    Args:
        agent_type: Optional agent type for agent-aware streaming

    Returns:
        Streaming callback handler instance
    """
    if agent_type:
        return AgentStreamingCallbackHandler(agent_type)
    return ChainlitStreamingCallbackHandler()


# Example usage with LangChain LLM
async def stream_llm_response(llm, prompt: str, agent_type: Optional[str] = None):
    """
    Helper function to stream LLM response to Chainlit.

    Args:
        llm: LangChain LLM instance
        prompt: The prompt to send to LLM
        agent_type: Optional agent type for display

    Returns:
        The generated response
    """
    # Get streaming callback
    callback = get_streaming_callback(agent_type)

    # Generate with streaming
    response = await llm.ainvoke(
        prompt,
        config={"callbacks": [callback]}
    )

    return response