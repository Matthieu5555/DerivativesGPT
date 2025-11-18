"""
Educational Agent Graph - Enhanced
===================================
LangGraph implementation for educational agent with:
- Topic continuity tracking (same topic vs topic change)
- Structured explanations (TL;DR → Formal Definition)
- Conversational follow-up mode
- Web search integration
- Iterative improvement loop

Flow Overview:
  Entry → Topic Classification → [New Topic] → Full Structured Explanation
                                 ↓
                          [Follow-up] → Conversational Response
                                 ↓
                          Quality Loop (if initial) → Verification → Exit
"""

from langgraph.graph import StateGraph, END
from typing import Literal
import logging

from derivatives_gpt_core.agents.educational.state import EducationalState

# Import educational nodes
from derivatives_gpt_core.agents.educational.nodes.classify_topic_continuity import classify_topic_continuity
from derivatives_gpt_core.agents.educational.nodes.generate_explanation import generate_explanation
from derivatives_gpt_core.agents.educational.nodes.critique_explanation import critique_explanation
from derivatives_gpt_core.agents.educational.nodes.rewrite_explanation import rewrite_explanation
from derivatives_gpt_core.agents.educational.nodes.verify_understanding import verify_understanding
from derivatives_gpt_core.agents.educational.nodes.reflect_on_learning import reflect_on_learning
from derivatives_gpt_core.agents.educational.nodes.assess_comprehension import assess_comprehension
from derivatives_gpt_core.agents.educational.nodes.build_on_understanding import build_on_understanding

# Import shared nodes
from derivatives_gpt_core.agents.shared.nodes.augment_with_context import augment_with_context
from derivatives_gpt_core.agents.shared.nodes.web_search import web_search

logger = logging.getLogger(__name__)


def build_educational_agent_graph() -> StateGraph:
    """
    Build enhanced educational agent graph with topic tracking and web search.

    New Flow:
    ```
    START
      ↓
    classify_topic_continuity  # Determines same topic vs new topic
      ↓
    check_rag
      ├─ [No RAG] → web_search
      └─ [Need RAG] → rag_retrieval → web_search
           ↓
    generate_explanation  # Uses conversation_mode (initial vs followup)
      ↓
    [Followup mode] → finalize → END
    [Initial mode] → assess_quality
      ├─ [Quality ≥ 0.7] → verify_understanding → reflect_on_learning → finalize → END
      └─ [Quality < 0.7 & attempts < 3] → rewrite → generate (loop)
           ↓
      [attempts ≥ 3] → verify_understanding → reflect_on_learning → finalize → END
    ```

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building enhanced educational agent graph")

    # Create graph with EducationalState
    graph = StateGraph(EducationalState)

    # ========================================================================
    # NODES
    # ========================================================================

    # Check if RAG retrieval needed
    def check_rag_status(state: EducationalState) -> dict:
        """Check if we need RAG retrieval."""
        if state.rag_sources and len(state.rag_sources) > 0:
            logger.info("RAG sources already available, skipping retrieval")
            return {}
        else:
            logger.info("RAG sources needed")
            return {}

    # Finalize explanation
    def finalize_explanation(state: EducationalState) -> dict:
        """
        Mark explanation as complete and update conversation state.

        For followup mode: Ready for next question
        For initial mode: Mark awaiting user followup
        """
        edu_context = state.educational_context
        mode = edu_context.conversation_mode

        if mode == "initial_explanation":
            # After initial explanation, mark as awaiting user understanding
            updated_context = edu_context.model_dump()
            updated_context["awaiting_user_understanding"] = True  # Human-in-the-loop: awaiting their explanation
            updated_context["awaiting_user_followup"] = True
            updated_context["conversation_mode"] = "followup_conversation"  # Switch mode for next turn

            logger.info("Initial explanation complete, awaiting user understanding check")
            return {
                "response_type": "explain_concept",
                "current_agent": "educational",
                "educational_context": updated_context
            }
        else:
            logger.info("Follow-up answer complete")
            return {
                "response_type": "explain_concept",
                "current_agent": "educational",
                "educational_context": edu_context.model_dump()
            }

    # Add nodes
    graph.add_node("classify_topic", classify_topic_continuity)
    graph.add_node("check_rag", check_rag_status)
    graph.add_node("rag_retrieval", augment_with_context)
    graph.add_node("web_search", web_search)
    graph.add_node("generate_explanation", generate_explanation)
    graph.add_node("assess_quality", critique_explanation)
    graph.add_node("rewrite_explanation", rewrite_explanation)
    graph.add_node("verify_understanding", verify_understanding)
    graph.add_node("reflect_on_learning", reflect_on_learning)
    graph.add_node("assess_comprehension", assess_comprehension)  # NEW: Assess user understanding
    graph.add_node("build_on_understanding", build_on_understanding)  # NEW: Build on user understanding
    graph.add_node("finalize", finalize_explanation)

    # ========================================================================
    # EDGES & ROUTING
    # ========================================================================

    # Entry point
    graph.set_entry_point("classify_topic")

    # From classify_topic → route based on whether user is explaining understanding
    def route_after_topic_classification(state: EducationalState) -> Literal["assess_comprehension", "check_rag"]:
        """
        Route based on whether this is an understanding check response:
        - If user is explaining their understanding → assess_comprehension
        - Otherwise → normal flow (check_rag)
        """
        if state.educational_context.user_explained_understanding:
            logger.info("Understanding check response detected - routing to assessment")
            return "assess_comprehension"
        else:
            logger.info("Regular question - routing to normal flow")
            return "check_rag"

    graph.add_conditional_edges(
        "classify_topic",
        route_after_topic_classification,
        {
            "assess_comprehension": "assess_comprehension",
            "check_rag": "check_rag"
        }
    )

    # From check_rag → conditional (rag needed?)
    def route_after_rag_check(state: EducationalState) -> Literal["rag_retrieval", "web_search"]:
        """Route to RAG retrieval if needed, else directly to web search."""
        if state.rag_sources and len(state.rag_sources) > 0:
            return "web_search"  # Already have RAG, skip retrieval
        else:
            return "rag_retrieval"  # Need RAG

    graph.add_conditional_edges(
        "check_rag",
        route_after_rag_check,
        {
            "rag_retrieval": "rag_retrieval",
            "web_search": "web_search"
        }
    )

    # From RAG retrieval → web search
    graph.add_edge("rag_retrieval", "web_search")

    # From web search → generate explanation
    graph.add_edge("web_search", "generate_explanation")

    # From generate_explanation → route based on conversation mode
    def route_after_generation(state: EducationalState) -> Literal["assess_quality", "finalize"]:
        """
        Route based on conversation mode:
        - initial_explanation: Go to quality assessment
        - followup_conversation: Skip quality check, finalize directly
        """
        mode = state.educational_context.conversation_mode

        if mode == "initial_explanation":
            logger.info("Initial explanation mode: assessing quality")
            return "assess_quality"
        else:  # followup_conversation
            logger.info("Follow-up mode: skipping quality assessment")
            return "finalize"

    graph.add_conditional_edges(
        "generate_explanation",
        route_after_generation,
        {
            "assess_quality": "assess_quality",
            "finalize": "finalize"
        }
    )

    # From assess_quality → route based on quality score
    def route_after_quality_assessment(state: EducationalState) -> Literal["rewrite_explanation", "verify_understanding"]:
        """
        Route based on quality score and attempt count:
        - Quality ≥ 0.7: Verify understanding
        - Quality < 0.7 & attempts < 3: Rewrite
        - Quality < 0.7 & attempts ≥ 3: Accept and verify
        """
        quality_score = state.explanation_quality_score or 0
        attempts = state.explanation_attempt_count or 0

        if quality_score >= 0.7:
            logger.info(f"Quality good ({quality_score:.2f}), proceeding to verification")
            return "verify_understanding"
        elif attempts >= 3:
            logger.warning(f"Max attempts reached, accepting current (quality: {quality_score:.2f})")
            return "verify_understanding"
        else:
            logger.info(f"Quality low ({quality_score:.2f}), rewriting (attempt {attempts + 1}/3)")
            return "rewrite_explanation"

    graph.add_conditional_edges(
        "assess_quality",
        route_after_quality_assessment,
        {
            "rewrite_explanation": "rewrite_explanation",
            "verify_understanding": "verify_understanding"
        }
    )

    # From rewrite → generate (loop back)
    graph.add_edge("rewrite_explanation", "generate_explanation")

    # From verify_understanding → conditional (skip reflection for initial explanations)
    def route_after_verification(state: EducationalState) -> Literal["reflect_on_learning", "finalize"]:
        """
        Skip reflection for initial explanations to show Iron Condor format in Chainlit.
        Only add reflection for follow-ups.
        """
        mode = state.educational_context.conversation_mode
        if mode == "initial_explanation":
            logger.info("Initial explanation: skipping reflection to show structured format")
            return "finalize"
        else:
            logger.info("Follow-up: adding reflection")
            return "reflect_on_learning"

    graph.add_conditional_edges(
        "verify_understanding",
        route_after_verification,
        {
            "reflect_on_learning": "reflect_on_learning",
            "finalize": "finalize"
        }
    )

    # From reflection → finalize (when used)
    graph.add_edge("reflect_on_learning", "finalize")

    # === HUMAN-IN-THE-LOOP FLOW ===
    # From assess_comprehension → build_on_understanding
    graph.add_edge("assess_comprehension", "build_on_understanding")

    # From build_on_understanding → finalize
    graph.add_edge("build_on_understanding", "finalize")

    # From finalize → END
    graph.add_edge("finalize", END)

    # Compile
    compiled = graph.compile()
    logger.info("Enhanced educational agent graph compiled successfully")

    return compiled


def create_educational_agent() -> StateGraph:
    """
    Factory function to create educational agent graph.

    Returns:
        Compiled educational agent graph
    """
    return build_educational_agent_graph()


if __name__ == "__main__":
    # Test graph compilation
    print("Testing enhanced educational agent graph compilation...")
    graph = build_educational_agent_graph()
    print("Graph compiled successfully!")

    # Use proper visualization for development
    from derivatives_gpt_core.utils.graph_visualization import save_graph_visualization
    save_graph_visualization(graph, "educational_graph.png", format="png")
