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
            # After initial explanation, mark as awaiting followup
            updated_context = edu_context.dict()
            edu_context_obj = state.educational_context.__class__(**updated_context)
            edu_context_obj.mark_followup()

            logger.info("Initial explanation complete, awaiting user follow-up")
            return {
                "response_type": "explain_concept",
                "current_agent": "educational",
                "educational_context": edu_context_obj
            }
        else:
            logger.info("Follow-up answer complete")
            return {
                "response_type": "explain_concept",
                "current_agent": "educational"
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
    graph.add_node("reflect_on_learning", reflect_on_learning)  # NEW: Learning reflection
    graph.add_node("finalize", finalize_explanation)

    # ========================================================================
    # EDGES & ROUTING
    # ========================================================================

    # Entry point
    graph.set_entry_point("classify_topic")

    # From classify_topic → check_rag (always)
    graph.add_edge("classify_topic", "check_rag")

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


# ============================================================================
# VISUALIZATION
# ============================================================================

def visualize_educational_graph():
    """
    Generate visual representation of the enhanced educational graph.

    Returns ASCII art diagram of the graph flow.
    """
    diagram = """
Enhanced Educational Agent Graph
=================================

                        ┌──────────────────┐
                        │      START       │
                        │  (User Question) │
                        └────────┬─────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ classify_topic         │
                    │ • Same topic?          │
                    │ • Topic change?        │
                    │ • Financial-related?   │
                    └──────────┬─────────────┘
                               │
                               ▼
                    ┌────────────────────────┐
                    │  check_rag             │
                    └──────────┬─────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
            [No RAG sources]      [Has RAG sources]
                    │                     │
                    ▼                     │
            ┌─────────────┐               │
            │rag_retrieval│               │
            └──────┬──────┘               │
                   │                      │
                   └──────────┬───────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   web_search     │
                    │  (Tavily API)    │
                    └────────┬─────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │ generate_explanation    │
                │ Mode: initial/followup  │
                │ Template: structured    │
                └──────────┬──────────────┘
                           │
                ┌──────────┴───────────┐
                │                      │
         [followup mode]        [initial mode]
                │                      │
                ▼                      ▼
         ┌────────────┐      ┌──────────────────┐
         │  finalize  │      │  assess_quality  │
         └─────┬──────┘      └────────┬─────────┘
               │                      │
               │           ┌──────────┴──────────┐
               │           │                     │
               │    [Quality ≥ 0.7]      [Quality < 0.7]
               │           │             [attempts < 3]
               │           │                     │
               │           ▼                     ▼
               │    ┌─────────────┐    ┌──────────────────┐
               │    │  verify_    │    │ rewrite_         │
               │    │understanding│    │ explanation      │
               │    └──────┬──────┘    └────────┬─────────┘
               │           │                    │
               │           │                    └─────────┐
               │           │                              │
               │           ▼                              │
               │    ┌────────────┐          (loop back to generate)
               │    │  finalize  │
               │    └─────┬──────┘
               │          │
               └──────────┴──────────┐
                                     │
                                     ▼
                              ┌───────────┐
                              │    END    │
                              └───────────┘

Key Features:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic continuity tracking (same topic vs new topic)
- Web search integration (Tavily) for latest information
- Dual conversation modes:
   • initial_explanation: Full structured template (TL;DR → Formal)
   • followup_conversation: Concise, conversational answers
- Quality-based iterative improvement (max 3 attempts)
- RAG + Web search augmentation
- Verification questions for comprehension check
"""
    return diagram


if __name__ == "__main__":
    # Test graph compilation
    print("Testing enhanced educational agent graph compilation...")
    graph = build_educational_agent_graph()
    print("Graph compiled successfully!")
    print(visualize_educational_graph())
