"""LangGraph CLI entrypoint - provides compiled graph for langgraph dev."""

from derivatives_gpt_core.agent_graph_definition import create_option_pricing_graph


def get_graph():
    """
    Synchronous entrypoint for LangGraph CLI.

    LangGraph dev server handles persistence automatically,
    so we pass None as the checkpointer.

    Returns:
        Compiled LangGraph Pregel instance
    """
    # LangGraph API handles checkpointing automatically
    # Pass None to avoid the custom checkpointer error
    graph = create_option_pricing_graph(checkpointer=None)
    return graph


# Export for LangGraph CLI
agent = get_graph()
