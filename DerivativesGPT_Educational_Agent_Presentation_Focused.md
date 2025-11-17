
# DerivativesGPT: A Deep Dive into the Educational Agent

An Agentic AI Case Study for CS-421

---

## Page 2 of 12

### Agenda

1.  **High-Level System Architecture**
    *   An Orchestra of Agents
2.  **Focus: The Educational Agent**
    *   Role & How It's Triggered
3.  **Inside the Educational Agent: A Hierarchical Graph**
    *   The Agent's State & Workflow
    *   Core Nodes: Research, Synthesis, and Critique
4.  **Connecting to Core Course Concepts**
    *   Agentic Search, Persistence & Human-in-the-Loop
5.  **Conclusion**

---

## Page 3 of 12

### High-Level System Architecture

DerivativesGPT is a multi-agent system orchestrated by a central LangGraph state machine.

*   A **Main Graph** receives all user queries.
*   An initial **`classify_user_intent`** node determines the user's goal.
*   The Main Graph **routes the task** to a specialized agent.

The system contains several agents (e.g., `Pricing`, `Educational`), but for this course, **we will focus exclusively on the Educational Agent.**

![High-Level-Architecture-Diagram](https://i.imgur.com/9y5J2Qc.png)

---

## Page 4 of 12

### The Educational Agent's Role

The Educational Agent acts as a **financial research assistant**. Its purpose is to provide clear, context-aware explanations of complex financial concepts.

**How it's Triggered:**

The Main Graph routes to the educational agent when a user's intent is classified as a request for an explanation.

```python
# From derivatives_gpt_core/core/graph/graph_builder.py

# The main graph's routing logic
workflow.add_conditional_edges(
    "classify",
    route_after_initial_classification,
    {
        "augment_with_context": "augment_with_context", # Leads to Pricing
        "off_topic": "off_topic",
        "explain_concept": "explain_concept"  # Triggers the Educational Agent
    }
)
```

---

## Page 5 of 12

### Inside the Agent: A Hierarchical Graph

The Educational Agent is not just a single function; it's a complete, self-contained **`StateGraph`**. This demonstrates a powerful hierarchical agent design.

This sub-graph has its own dedicated state, nodes, and internal routing logic, allowing it to manage a complex workflow independently.

**Agent's Internal Structure:**
*   `graph.py`: Defines the agent's LangGraph workflow.
*   `state.py`: Defines the agent's unique state object.
*   `nodes/`: Contains the specific functions (skills) the agent can execute.

```python
# From /agents/educational/graph.py

def build_educational_agent_graph() -> StateGraph:
    """Builds the self-contained graph for the educational agent."""
    
    # The agent uses its own specific state
    graph = StateGraph(EducationalState)

    # Add nodes for its specific workflow
    graph.add_node("classify_topic", classify_topic_continuity)
    graph.add_node("rag_retrieval", augment_with_context)
    graph.add_node("web_search", web_search)
    graph.add_node("generate_explanation", generate_explanation)
    graph.add_node("assess_quality", critique_explanation)
    graph.add_node("rewrite_explanation", rewrite_explanation)
    
    # Define entry point and edges...
    graph.set_entry_point("classify_topic")
    
    # ...
    
    return graph.compile()
```

---

## Page 6 of 12

### The Agent's State

A core concept in LangGraph is the `State` object. The Educational Agent has its own specialized state that extends the `BaseAgentState`, allowing it to track information relevant only to its task.

This is a practical example of modular state management.

```python
# From /agents/educational/state.py

class EducationalState(BaseAgentState):
    """State for the educational agent."""

    # --- Explanation Generation ---
    explanation_text: str | None = Field(...)
    explanation_quality_score: float | None = Field(...)
    explanation_attempt_count: int = Field(default=0)
    explanation_critique: dict | None = Field(...)

    # --- User Comprehension ---
    verification_questions: list[str] = Field(default_factory=list)
    
    # --- Conversation Tracking ---
    educational_context: EducationalConversationState = Field(...)
```

---

## Page 7 of 12

### Core Workflow: A Researcher's Loop

The agent's internal graph simulates a researcher's workflow: **Research -> Draft -> Critique -> Revise**.

1.  **Research (Agentic Search):** Gathers information from multiple sources.
    *   `rag_retrieval`: Looks up foundational knowledge in a local vector database.
    *   `web_search`: Searches the web for real-time, supplementary information.

2.  **Draft (`generate_explanation`):** Synthesizes the gathered information into a structured explanation.

3.  **Critique (`assess_quality`):** A separate LLM call evaluates the generated explanation for clarity, accuracy, and completeness.

4.  **Revise (`rewrite_explanation`):** If the quality is low, the agent rewrites the explanation based on the critique, looping back to the `generate_explanation` node.

---

## Page 8 of 12

### Code Snippet: The Critique & Rewrite Loop

This conditional edge is the heart of the agent's self-improvement capability. It's a powerful pattern for increasing output quality.

This directly implements the idea of using LLMs to "judge" or evaluate output, a key technique in building reliable agentic systems.

```python
# From /agents/educational/graph.py

def route_after_quality_assessment(state: EducationalState):
    """Route based on quality score and attempt count."""
    quality_score = state.explanation_quality_score or 0
    attempts = state.explanation_attempt_count or 0

    if quality_score >= 0.7:
        # If quality is high, proceed
        return "verify_understanding"
    elif attempts >= 3:
        # If max attempts reached, accept the current version
        return "verify_understanding"
    else:
        # If quality is low, trigger the rewrite node
        return "rewrite_explanation"

# This logic is added as a conditional edge to the graph
graph.add_conditional_edges(
    "assess_quality",
    route_after_quality_assessment,
    {
        "rewrite_explanation": "rewrite_explanation",
        "verify_understanding": "verify_understanding"
    }
)
```

---

## Page 9 of 12

### Persistence & Conversational Memory

To handle follow-up questions, the agent needs to remember the context of the conversation. This is achieved through **checkpointing**, a core feature of LangGraph.

*   A `checkpointer` is passed when the main graph is compiled.
*   LangGraph automatically saves the full application state after each step.
*   When the user sends a new message in the same conversation, the agent reloads the state and knows what was discussed previously.

```python
# From derivatives_gpt_core/core/graph/graph_builder.py

def create_option_pricing_graph(checkpointer: BaseCheckpointSaver | None):
    
    # ... graph definition ...

    # The checkpointer enables persistence for the entire application,
    # including the educational agent's state.
    graph = workflow.compile(checkpointer=checkpointer)

    return graph
```

---

## Page 10 of 12

### Human-in-the-Loop

While the critique loop is an example of an automated feedback loop, the system is fundamentally designed for human interaction.

The most direct example in the educational context is the **conversational nature** of the agent.

*   The agent's ability to handle **follow-up questions** (`classify_topic_continuity` node) is a form of human-in-the-loop, where the user guides the exploration of a topic.
*   The `verify_understanding` node can generate questions for the user, creating an interactive learning experience where the agent adapts based on the user's responses.

This fulfills the project requirement of creating an agent that allows for "user interaction for refinement."

---

## Page 11 of 12

### Mapping to Course Concepts

The Educational Agent is a microcosm of the entire course, demonstrating each key concept in a focused, practical way.

| Session | Topic | Implementation in the Educational Agent |
| :--- | :--- | :--- |
| **1-3** | **LangGraph Fundamentals** | A hierarchical `StateGraph` with its own state (`EducationalState`), nodes, and conditional edges. |
| **4** | **Agentic Search** | The `rag_retrieval` and `web_search` nodes work in tandem to gather comprehensive information. |
| **5** | **Persistence** | The application-wide `checkpointer` saves and reloads the `EducationalState`, enabling multi-turn educational dialogues. |
| **6** | **Human-in-the-Loop** | The agent's ability to process follow-up questions and verify user understanding makes the user a key part of the learning loop. |
| **7** | **Agent Workflow Design** | The "Research -> Draft -> Critique -> Revise" loop perfectly simulates the workflow of a researcher drafting a paper. |

---

## Page 12 of 12

### Conclusion

The Educational Agent in DerivativesGPT is a powerful, self-contained module that demonstrates how to build sophisticated, controllable agents with LangGraph.

**Key Architectural Patterns:**

*   **Hierarchical Graphs:** A main graph for orchestration and specialized sub-graphs for complex tasks.
*   **Modular State:** Each agent can have its own state, keeping the system clean and scalable.
*   **Iterative Improvement:** Using LLM-based critique and conditional logic to create self-correcting workflows.

This case study provides a complete, practical blueprint for the final course project.
