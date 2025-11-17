"""Test RAG integration end-to-end."""

import pytest
from derivatives_gpt_core.rag.hybrid_retriever import HybridRAGRetriever, get_rag_retriever
from derivatives_gpt_core.config import get_settings


def test_hybrid_retriever_initialization():
    """Test retriever loads FAISS and metadata."""
    try:
        retriever = HybridRAGRetriever()
        assert retriever.index is not None
        assert len(retriever.metadata) > 0
        assert retriever.bm25 is not None
        assert retriever.embedder is not None
    except FileNotFoundError:
        pytest.skip("RAG vectorstore files not found (optional test)")


def test_retrieve_black_scholes():
    """Test retrieval for Black-Scholes query."""
    try:
        retriever = get_rag_retriever()
        results = retriever.retrieve("Black-Scholes formula")

        assert len(results) > 0
        assert len(results) <= 3  # final_top_k default is 3

        # Check structure
        for result in results:
            assert "text" in result
            assert "book" in result
            assert "page" in result
            assert "score" in result
            assert "chunk_id" in result

            # Check types
            assert isinstance(result["text"], str)
            assert isinstance(result["book"], str)
            assert isinstance(result["page"], int)
            assert isinstance(result["score"], float)

    except FileNotFoundError:
        pytest.skip("RAG vectorstore files not found (optional test)")


def test_retrieve_empty_query():
    """Test graceful handling of empty query."""
    try:
        retriever = get_rag_retriever()
        results = retriever.retrieve("")

        assert results == []

    except FileNotFoundError:
        pytest.skip("RAG vectorstore files not found (optional test)")


def test_retrieve_concept_query():
    """Test concept explanation query."""
    try:
        retriever = get_rag_retriever()
        results = retriever.retrieve("What is delta hedging?")

        assert len(results) > 0

        # Check that scores are reasonable (> 0.0)
        for result in results:
            assert result["score"] > 0.0, f"Score should be positive: {result['score']}"

    except FileNotFoundError:
        pytest.skip("RAG vectorstore files not found (optional test)")


def test_config_settings():
    """Test RAG configuration is properly loaded."""
    settings = get_settings()

    # Check all RAG settings exist
    assert hasattr(settings, "rag_enabled")
    assert hasattr(settings, "rag_index_path")
    assert hasattr(settings, "rag_metadata_path")
    assert hasattr(settings, "rag_bm25_candidate_count")
    assert hasattr(settings, "rag_rerank_candidate_count")
    assert hasattr(settings, "rag_final_source_count")
    assert hasattr(settings, "rag_embedding_model")

    # Check types
    assert isinstance(settings.rag_enabled, bool)
    assert isinstance(settings.rag_index_path, str)
    assert isinstance(settings.rag_metadata_path, str)
    assert isinstance(settings.rag_bm25_candidate_count, int)
    assert isinstance(settings.rag_rerank_candidate_count, int)
    assert isinstance(settings.rag_final_source_count, int)
    assert isinstance(settings.rag_embedding_model, str)


def test_singleton_retriever():
    """Test that get_rag_retriever returns singleton."""
    try:
        retriever1 = get_rag_retriever()
        retriever2 = get_rag_retriever()

        # Should be the same instance
        assert retriever1 is retriever2

    except FileNotFoundError:
        pytest.skip("RAG vectorstore files not found (optional test)")


def test_retrieval_performance():
    """Test that retrieval completes in reasonable time."""
    import time

    try:
        retriever = get_rag_retriever()

        start = time.time()
        results = retriever.retrieve("option pricing")
        elapsed = time.time() - start

        # Should complete in less than 5 seconds
        assert elapsed < 5.0, f"Retrieval took too long: {elapsed:.2f}s"
        assert len(results) > 0

    except FileNotFoundError:
        pytest.skip("RAG vectorstore files not found (optional test)")
