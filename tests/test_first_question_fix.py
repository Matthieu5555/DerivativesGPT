"""Test that first question is correctly detected as new topic."""

import asyncio
from derivatives_gpt_core.agents.educational.nodes.classify_topic_continuity import classify_topic_continuity
from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.core.state.educational_state import EducationalConversationState
from langchain_core.messages import HumanMessage


async def test_first_question_detection():
    """Test that first question with no previous context is classified as new topic."""

    # Create state with NO previous context (first question)
    state = EducationalState(
        messages=[HumanMessage(content="What is delta and how does it affect option pricing?")],
        educational_context=EducationalConversationState(
            current_topic=None,  # No previous topic
            last_user_question=None,  # No previous question
        ),
        explanation_text=None,  # No previous explanation
    )

    print("Testing first question detection...")
    print(f"  Previous topic: {state.educational_context.current_topic}")
    print(f"  Previous question: {state.educational_context.last_user_question}")
    print(f"  Previous explanation: {state.explanation_text}")

    # Classify topic continuity
    result = await classify_topic_continuity(state)

    # Check classification
    edu_context = result["educational_context"]
    is_same_topic = edu_context.is_same_topic
    reasoning = edu_context.topic_classification_reasoning

    print(f"\nClassification result:")
    print(f"  is_same_topic: {is_same_topic}")
    print(f"  reasoning: {reasoning}")

    # Verify
    if is_same_topic is False:
        print("\n✅ PASS: First question correctly classified as NEW TOPIC")
        return True
    else:
        print("\n❌ FAIL: First question incorrectly classified as FOLLOW-UP")
        return False


async def test_actual_followup_detection():
    """Test that actual follow-up question is correctly detected."""

    # Create state with previous context (follow-up scenario)
    state = EducationalState(
        messages=[
            HumanMessage(content="What is delta?"),
            HumanMessage(content="What about gamma?"),
        ],
        educational_context=EducationalConversationState(
            current_topic="delta",
            last_user_question="What is delta?",
        ),
        explanation_text="Delta measures how much an option's price changes when the stock price moves $1...",
    )

    print("\nTesting follow-up question detection...")
    print(f"  Previous topic: {state.educational_context.current_topic}")
    print(f"  Previous question: {state.educational_context.last_user_question}")
    print(f"  Current question: {state.messages[-1].content}")

    # Classify topic continuity
    result = await classify_topic_continuity(state)

    # Check classification
    edu_context = result["educational_context"]
    is_same_topic = edu_context.is_same_topic
    reasoning = edu_context.topic_classification_reasoning

    print(f"\nClassification result:")
    print(f"  is_same_topic: {is_same_topic}")
    print(f"  reasoning: {reasoning}")

    # Verify (should be True for follow-up)
    if is_same_topic is True:
        print("\n✅ PASS: Follow-up question correctly classified as SAME TOPIC")
        return True
    else:
        print("\n❌ FAIL: Follow-up question incorrectly classified as NEW TOPIC")
        return False


async def main():
    """Run all tests."""
    print("="*60)
    print("Testing First Question Detection Fix")
    print("="*60)

    test1_result = await test_first_question_detection()
    test2_result = await test_actual_followup_detection()

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    if test1_result and test2_result:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
        if not test1_result:
            print("  - First question detection: FAILED")
        if not test2_result:
            print("  - Follow-up detection: FAILED")


if __name__ == "__main__":
    asyncio.run(main())
