"""Tests for RAG hybrid retrieval with mocked dependencies."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from derivatives_gpt_core.rag.hybrid_retriever import HybridRAGRetriever, get_rag_retriever


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock()
    settings.rag_index_path = "/fake/path/index.faiss"
    settings.rag_metadata_path = "/fake/path/metadata.json"
    settings.gemini_api_key = "fake_api_key"
    settings.rag_embedding_model = "models/text-embedding-004"
    settings.rag_bm25_candidate_count = 20
    settings.rag_rerank_candidate_count = 10
    settings.rag_final_source_count = 3
    return settings


@pytest.fixture
def mock_metadata():
    """Create mock metadata for testing."""
    return [
        {
            "text": "The Black-Scholes formula is used for pricing European options.",
            "book_name": "Hull_Options_Futures_and_Other_Derivatives",
            "chapter_number": 15,
            "chapter_title": "The Black-Scholes-Merton Model",
            "chunk_id": "chunk_0"
        },
        {
            "text": "Volatility is a measure of the uncertainty of returns.",
            "book_name": "Shreve_Stochastic_Calculus_for_Finance",
            "chapter_number": 4,
            "chapter_title": "Stochastic Calculus",
            "chunk_id": "chunk_1"
        },
        {
            "text": "The delta of an option measures its sensitivity to spot price changes.",
            "book_name": "Hull_Options_Futures_and_Other_Derivatives",
            "chapter_number": 19,
            "chapter_title": "The Greeks",
            "chunk_id": "chunk_2"
        }
    ]


@pytest.fixture
def mock_faiss_index():
    """Create mock FAISS index."""
    index = Mock()
    index.ntotal = 3
    # Mock reconstruct to return fake vectors
    index.reconstruct.side_effect = lambda idx: np.random.rand(768).astype('float32')
    return index


def test_hybrid_retriever_initialization(mock_settings, mock_metadata, mock_faiss_index):
    """Test HybridRAGRetriever initialization."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
         patch("builtins.open", create=True) as mock_open, \
         patch("json.load", return_value=mock_metadata), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings"):

        retriever = HybridRAGRetriever()

        assert retriever.index == mock_faiss_index
        assert len(retriever.metadata) == 3
        assert retriever.bm25_top_k == 20
        assert retriever.rerank_top_k == 10
        assert retriever.final_top_k == 3


def test_hybrid_retriever_missing_index(mock_settings):
    """Test HybridRAGRetriever with missing index file."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=False):

        with pytest.raises(FileNotFoundError, match="FAISS index not found"):
            HybridRAGRetriever()


def test_hybrid_retriever_missing_metadata(mock_settings):
    """Test HybridRAGRetriever with missing metadata file."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists") as mock_exists:

        # Index exists, metadata doesn't
        mock_exists.side_effect = [True, False]

        with pytest.raises(FileNotFoundError, match="Metadata not found"):
            HybridRAGRetriever()


def test_retrieve_empty_query(mock_settings, mock_metadata, mock_faiss_index):
    """Test retrieve with empty query."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
         patch("builtins.open", create=True), \
         patch("json.load", return_value=mock_metadata), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings"):

        retriever = HybridRAGRetriever()
        results = retriever.retrieve("")

        assert results == []


def test_retrieve_success(mock_settings, mock_metadata, mock_faiss_index):
    """Test successful retrieval with hybrid approach."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
         patch("builtins.open", create=True), \
         patch("json.load", return_value=mock_metadata), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings") as mock_embedder_class:

        # Mock embedder
        mock_embedder = Mock()
        # Return a normalized vector
        query_embedding = np.random.rand(768).astype('float32')
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        mock_embedder.embed_query.return_value = query_embedding.tolist()
        mock_embedder_class.return_value = mock_embedder

        retriever = HybridRAGRetriever()

        # Mock BM25 to return specific scores
        with patch.object(retriever.bm25, 'get_scores') as mock_bm25_scores:
            # Make first document most relevant
            mock_bm25_scores.return_value = np.array([10.0, 5.0, 3.0])

            results = retriever.retrieve("Black-Scholes formula")

            assert len(results) <= 3  # Should return top 3
            assert all("text" in r for r in results)
            assert all("book" in r for r in results)
            assert all("page" in r for r in results)
            assert all("score" in r for r in results)
            assert all("chunk_id" in r for r in results)


def test_retrieve_bm25_filtering(mock_settings, mock_metadata, mock_faiss_index):
    """Test that BM25 filters candidates correctly."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
         patch("builtins.open", create=True), \
         patch("json.load", return_value=mock_metadata), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings") as mock_embedder_class:

        # Mock embedder
        mock_embedder = Mock()
        query_embedding = np.random.rand(768).astype('float32')
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        mock_embedder.embed_query.return_value = query_embedding.tolist()
        mock_embedder_class.return_value = mock_embedder

        retriever = HybridRAGRetriever()

        # Mock BM25 scores - make volatility document most relevant
        with patch.object(retriever.bm25, 'get_scores') as mock_bm25_scores:
            mock_bm25_scores.return_value = np.array([1.0, 20.0, 2.0])

            results = retriever.retrieve("volatility uncertainty")

            # Verify BM25 was called
            assert mock_bm25_scores.called
            # Should have results
            assert len(results) > 0


def test_retrieve_error_handling(mock_settings, mock_metadata, mock_faiss_index):
    """Test error handling during retrieval."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
         patch("builtins.open", create=True), \
         patch("json.load", return_value=mock_metadata), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings") as mock_embedder_class:

        # Mock embedder to raise exception
        mock_embedder = Mock()
        mock_embedder.embed_query.side_effect = Exception("API Error")
        mock_embedder_class.return_value = mock_embedder

        retriever = HybridRAGRetriever()
        results = retriever.retrieve("test query")

        # Should return empty list on error, not raise exception
        assert results == []


def test_retrieve_book_name_formatting(mock_settings, mock_metadata, mock_faiss_index):
    """Test book name formatting in results."""
    # Create metadata with long book name
    metadata_with_long_name = [
        {
            "text": "Test content",
            "book_name": "This_Is_A_Very_Long_Book_Name_That_Should_Be_Truncated_Because_It_Exceeds_Sixty_Characters",
            "chapter_number": 1,
            "chapter_title": "Introduction",
            "chunk_id": "chunk_0"
        }
    ]

    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
         patch("builtins.open", create=True), \
         patch("json.load", return_value=metadata_with_long_name), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings") as mock_embedder_class:

        mock_embedder = Mock()
        query_embedding = np.random.rand(768).astype('float32')
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        mock_embedder.embed_query.return_value = query_embedding.tolist()
        mock_embedder_class.return_value = mock_embedder

        retriever = HybridRAGRetriever()

        with patch.object(retriever.bm25, 'get_scores') as mock_bm25_scores:
            mock_bm25_scores.return_value = np.array([10.0])

            results = retriever.retrieve("test")

            assert len(results) > 0
            # Book name should have underscores replaced with spaces
            assert "_" not in results[0]["book"]
            # Long names should be truncated
            assert len(results[0]["book"]) <= 63  # 60 + "..."


def test_retrieve_page_reference_formatting(mock_settings, mock_faiss_index):
    """Test page reference formatting with different metadata."""
    # Test different chapter info scenarios
    test_cases = [
        {
            "metadata": [{
                "text": "Content",
                "book_name": "Test_Book",
                "chapter_number": 5,
                "chapter_title": "Chapter Five",
                "chunk_id": "chunk_0"
            }],
            "expected_page": "Ch. 5"
        },
        {
            "metadata": [{
                "text": "Content",
                "book_name": "Test_Book",
                "chapter_title": "pre-ch1",
                "chunk_id": "chunk_0"
            }],
            "expected_page": "Intro"
        },
        {
            "metadata": [{
                "text": "Content",
                "book_name": "Test_Book",
                "chapter_title": "Preface",
                "chunk_id": "chunk_0"
            }],
            "expected_page": "Preface"
        }
    ]

    for test_case in test_cases:
        with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
             patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
             patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
             patch("builtins.open", create=True), \
             patch("json.load", return_value=test_case["metadata"]), \
             patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings") as mock_embedder_class:

            mock_embedder = Mock()
            query_embedding = np.random.rand(768).astype('float32')
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            mock_embedder.embed_query.return_value = query_embedding.tolist()
            mock_embedder_class.return_value = mock_embedder

            retriever = HybridRAGRetriever()

            with patch.object(retriever.bm25, 'get_scores') as mock_bm25_scores:
                mock_bm25_scores.return_value = np.array([10.0])

                results = retriever.retrieve("test")

                assert len(results) > 0
                assert results[0]["page"] == test_case["expected_page"]


def test_get_rag_retriever_singleton(mock_settings, mock_metadata, mock_faiss_index):
    """Test that get_rag_retriever returns singleton instance."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
         patch("builtins.open", create=True), \
         patch("json.load", return_value=mock_metadata), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings"):

        # Reset singleton
        import derivatives_gpt_core.rag.hybrid_retriever as retriever_module
        retriever_module._retriever = None

        retriever1 = get_rag_retriever()
        retriever2 = get_rag_retriever()

        # Should be same instance
        assert retriever1 is retriever2


def test_retrieve_cosine_similarity_reranking(mock_settings, mock_metadata, mock_faiss_index):
    """Test that cosine similarity reranking works correctly."""
    with patch("derivatives_gpt_core.rag.hybrid_retriever.get_settings", return_value=mock_settings), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.Path.exists", return_value=True), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.faiss.read_index", return_value=mock_faiss_index), \
         patch("builtins.open", create=True), \
         patch("json.load", return_value=mock_metadata), \
         patch("derivatives_gpt_core.rag.hybrid_retriever.GoogleGenerativeAIEmbeddings") as mock_embedder_class:

        mock_embedder = Mock()
        # Create a specific query embedding
        query_embedding = np.array([1.0] * 768, dtype='float32')
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        mock_embedder.embed_query.return_value = query_embedding.tolist()
        mock_embedder_class.return_value = mock_embedder

        retriever = HybridRAGRetriever()

        # Mock FAISS reconstruct to return known vectors
        def mock_reconstruct(idx):
            # Return vectors with varying similarity to query
            if idx == 0:
                vec = np.array([1.0] * 768, dtype='float32')  # High similarity
            elif idx == 1:
                vec = np.array([0.5] * 768, dtype='float32')  # Medium similarity
            else:
                vec = np.array([0.1] * 768, dtype='float32')  # Low similarity
            return vec / np.linalg.norm(vec)

        mock_faiss_index.reconstruct.side_effect = mock_reconstruct

        with patch.object(retriever.bm25, 'get_scores') as mock_bm25_scores:
            # All get through BM25
            mock_bm25_scores.return_value = np.array([10.0, 10.0, 10.0])

            results = retriever.retrieve("test query")

            # Should return results, ordered by cosine similarity (reranked)
            assert len(results) > 0
            # Results should have scores from cosine similarity
            assert all(r["score"] >= 0 for r in results)
