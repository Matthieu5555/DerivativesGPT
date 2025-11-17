#!/usr/bin/env python3
"""
Implementation Testing Script
==============================
Tests the full agent separation implementation to catch bugs before deployment.
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported."""
    print("\n" + "="*80)
    print("TEST 1: Import Validation")
    print("="*80)

    try:
        # Core state management
        from derivatives_gpt_core.core.state.agent_state_wrapper import (
            AgentStateWrapper, get_allowed_fields, AccessViolationError
        )
        print("✅ agent_state_wrapper imports OK")

        from derivatives_gpt_core.core.state.state_factory import (
            create_state_for_agent, detect_agent_from_message
        )
        print("✅ state_factory imports OK")

        from derivatives_gpt_core.core.state.agent_detection import detect_agent_type
        print("✅ agent_detection imports OK")

        # Routing
        from derivatives_gpt_core.core.graph.agent_routing import route_to_agent
        print("✅ agent_routing imports OK")

        # Checkpointing
        from derivatives_gpt_core.conversation_memory.agent_checkpoint_manager import (
            AgentCheckpointManager
        )
        print("✅ agent_checkpoint_manager imports OK")

        # LLM providers
        from derivatives_gpt_core.llm_provider_agents import get_llm_for_agent
        print("✅ llm_provider_agents imports OK")

        # Graphs
        from derivatives_gpt_core.agents.educational.graph import build_educational_agent_graph
        from derivatives_gpt_core.agents.pricing.graph import build_pricing_agent_graph
        from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
        print("✅ All graph imports OK")

        print("\n✅ ALL IMPORTS SUCCESSFUL")
        return True

    except ImportError as e:
        print(f"\n❌ IMPORT ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_detection():
    """Test agent detection functionality."""
    print("\n" + "="*80)
    print("TEST 2: Agent Detection")
    print("="*80)

    from derivatives_gpt_core.core.state.agent_detection import detect_agent_type

    test_cases = [
        ("What is delta?", "educational"),
        ("Price a call on AAPL", "pricing"),
        ("Hello", "unified"),
    ]

    passed = 0
    for query, expected in test_cases:
        result = detect_agent_type(query)
        actual = result.agent_type

        if actual == expected:
            print(f"✅ '{query}' → {actual} (expected {expected})")
            passed += 1
        else:
            print(f"❌ '{query}' → {actual} (expected {expected})")

    print(f"\n{passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_state_wrapper():
    """Test state wrapper with field access control."""
    print("\n" + "="*80)
    print("TEST 3: State Wrapper Field Access Control")
    print("="*80)

    from derivatives_gpt_core.core.state.agent_state_wrapper import (
        AgentStateWrapper, AccessViolationError
    )
    from derivatives_gpt_core.agents.shared.base_state import BaseAgentState

    # Create states for each agent type
    from derivatives_gpt_core.agents.educational.state import EducationalState
    from derivatives_gpt_core.agents.pricing.state import PricingState

    edu_state = EducationalState(messages=[])
    pricing_state = PricingState(messages=[])

    # Test educational agent
    print("\n📚 Testing Educational Agent:")
    edu_wrapper = AgentStateWrapper(edu_state, "educational", enforce=True)

    # Should be allowed
    try:
        edu_wrapper.set_field("explanation_text", "Test explanation")
        print("✅ Educational can write to explanation_text")
    except AccessViolationError:
        print("❌ Educational should be able to write to explanation_text")
        return False

    # Should be denied
    try:
        edu_wrapper.set_field("spot_price", 150.0)
        print("❌ Educational should NOT be able to write to spot_price")
        return False
    except AccessViolationError:
        print("✅ Educational correctly denied access to spot_price")

    # Test pricing agent
    print("\n💰 Testing Pricing Agent:")
    pricing_wrapper = AgentStateWrapper(pricing_state, "pricing", enforce=True)

    # Should be allowed
    try:
        pricing_wrapper.set_field("spot_price", 150.0)
        print("✅ Pricing can write to spot_price")
    except AccessViolationError:
        print("❌ Pricing should be able to write to spot_price")
        return False

    # Should be denied
    try:
        pricing_wrapper.set_field("explanation_text", "Test")
        print("❌ Pricing should NOT be able to write to explanation_text")
        return False
    except AccessViolationError:
        print("✅ Pricing correctly denied access to explanation_text")

    print("\n✅ ALL STATE WRAPPER TESTS PASSED")
    return True


def test_field_categorization():
    """Test that all fields are properly categorized."""
    print("\n" + "="*80)
    print("TEST 4: Field Categorization")
    print("="*80)

    from derivatives_gpt_core.core.state.agent_state_wrapper import (
        get_shared_fields, get_educational_fields, get_pricing_fields, get_rag_fields
    )

    shared = get_shared_fields()
    educational = get_educational_fields()
    pricing = get_pricing_fields()
    rag = get_rag_fields()

    print(f"📁 Shared fields: {len(shared)}")
    print(f"🎓 Educational fields: {len(educational)}")
    print(f"💰 Pricing fields: {len(pricing)}")
    print(f"📚 RAG fields: {len(rag)}")

    # Check for overlaps (educational and pricing should not overlap)
    overlap = educational & pricing
    if overlap:
        print(f"❌ OVERLAP DETECTED: {overlap}")
        return False
    else:
        print("✅ No educational-pricing overlap")

    # Check that important fields are categorized
    required_shared = ["messages", "response_type", "is_option_related"]
    required_edu = ["explanation_text", "user_understanding_score"]
    required_pricing = ["spot_price", "strike_price", "execution_plan"]

    missing = []
    for field in required_shared:
        if field not in shared:
            missing.append(f"shared:{field}")

    for field in required_edu:
        if field not in educational:
            missing.append(f"educational:{field}")

    for field in required_pricing:
        if field not in pricing:
            missing.append(f"pricing:{field}")

    if missing:
        print(f"❌ MISSING FIELDS: {missing}")
        return False
    else:
        print("✅ All required fields properly categorized")

    return True


def test_graph_compilation():
    """Test that graphs compile without errors."""
    print("\n" + "="*80)
    print("TEST 5: Graph Compilation")
    print("="*80)

    try:
        from derivatives_gpt_core.agents.educational.graph import build_educational_agent_graph
        from derivatives_gpt_core.agents.pricing.graph import build_pricing_agent_graph
        from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph

        print("🎓 Compiling educational graph...")
        edu_graph = build_educational_agent_graph()
        print("✅ Educational graph compiled")

        print("💰 Compiling pricing graph...")
        pricing_graph = build_pricing_agent_graph()
        print("✅ Pricing graph compiled")

        print("🤖 Compiling orchestrator graph...")
        orchestrator = build_orchestrator_graph()
        print("✅ Orchestrator graph compiled")

        print("\n✅ ALL GRAPHS COMPILED SUCCESSFULLY")
        return True

    except Exception as e:
        print(f"\n❌ GRAPH COMPILATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_checkpoint_manager():
    """Test checkpoint manager initialization."""
    print("\n" + "="*80)
    print("TEST 6: Checkpoint Manager")
    print("="*80)

    try:
        from derivatives_gpt_core.conversation_memory.agent_checkpoint_manager import (
            AgentCheckpointManager
        )

        # Use in-memory database for testing
        manager = AgentCheckpointManager(":memory:")

        # Test thread ID formatting
        thread_id = manager.format_agent_thread_id("session_123", "educational")
        expected = "session_123.educational"

        if thread_id == expected:
            print(f"✅ Thread ID formatting: {thread_id}")
        else:
            print(f"❌ Thread ID mismatch: {thread_id} != {expected}")
            return False

        # Test parsing
        base, agent = manager.parse_agent_thread_id(thread_id)
        if base == "session_123" and agent == "educational":
            print(f"✅ Thread ID parsing: {base}.{agent}")
        else:
            print(f"❌ Thread ID parsing failed")
            return False

        print("✅ CHECKPOINT MANAGER OK")
        return True

    except Exception as e:
        print(f"❌ CHECKPOINT MANAGER ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "AGENT SEPARATION IMPLEMENTATION TEST SUITE".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    tests = [
        ("Import Validation", test_imports),
        ("Agent Detection", test_agent_detection),
        ("State Wrapper", test_state_wrapper),
        ("Field Categorization", test_field_categorization),
        ("Graph Compilation", test_graph_compilation),
        ("Checkpoint Manager", test_checkpoint_manager),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ {name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {name}")

    print("="*80)
    print(f"TOTAL: {passed_count}/{total_count} tests passed ({passed_count/total_count*100:.1f}%)")
    print("="*80)

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Implementation is ready.")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed. Please fix before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
