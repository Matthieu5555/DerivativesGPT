"""Hybrid BM25 + FAISS retrieval for mathematical context."""

import json
import numpy as np
import faiss
from pathlib import Path
from rank_bm25 import BM25Okapi
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from derivatives_gpt_core.config import get_settings
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class HybridRAGRetriever:
    """
    Hybrid retrieval combining BM25 keyword search with FAISS vector reranking.

    Architecture:
    1. BM25 fast keyword search (top 20)
    2. Embed query with Google text-embedding-004
    3. Rerank BM25 results using cosine similarity (top 10)
    4. Return top 3 with metadata

    Called by: graph_nodes/rag_retrieval.py
    """

    def __init__(self):
        """Initialize retriever with config settings."""
        settings = get_settings()

        # Load FAISS index
        index_path = Path(settings.rag_index_path)
        metadata_path = Path(settings.rag_metadata_path)

        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found: {metadata_path}")

        try:
            self.index = faiss.read_index(str(index_path))
        except Exception as e:
            logger.error(f"Failed to load FAISS index from {index_path}: {e}")
            raise RuntimeError(f"Corrupted or unreadable FAISS index: {index_path}") from e

        try:
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse metadata JSON from {metadata_path}: {e}")
            raise RuntimeError(f"Corrupted metadata file: {metadata_path}") from e

        logger.info(f"Loaded FAISS index: {self.index.ntotal} vectors, {len(self.metadata)} metadata entries")

        # Build BM25 index from metadata texts
        texts = [m.get('text', '') for m in self.metadata]
        tokenized_texts = [text.lower().split() for text in texts]
        self.bm25 = BM25Okapi(tokenized_texts)

        # Initialize embedder
        api_key = settings.gemini_api_key
        self.embedder = GoogleGenerativeAIEmbeddings(
            model=settings.rag_embedding_model,
            google_api_key=api_key,
            task_type="retrieval_query"
        )

        # Config
        self.bm25_top_k = settings.rag_bm25_candidate_count
        self.rerank_top_k = settings.rag_rerank_candidate_count
        self.final_top_k = settings.rag_final_source_count

        logger.info(f"HybridRAGRetriever initialized: BM25={self.bm25_top_k}, rerank={self.rerank_top_k}, final={self.final_top_k}")

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve top-k relevant sources using hybrid approach.

        Args:
            query: User query string

        Returns:
            List of dicts with keys: text, book, page, score, chunk_id

        Example:
            results = retriever.retrieve("Black-Scholes formula")
            # [{'text': '...', 'book': 'Hull', 'page': 42, 'score': 0.89, 'chunk_id': '123'}, ...]
        """
        try:
            if not query or not query.strip():
                logger.warning("Empty query provided to RAG retriever")
                return []

            # Step 1: BM25 keyword search
            tokens = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokens)
            top_bm25_indices = np.argsort(bm25_scores)[-self.bm25_top_k:][::-1]

            logger.debug(f"BM25 found {len(top_bm25_indices)} candidates")

            # Step 2: Embed query
            embedding = self.embedder.embed_query(query)
            query_vec = np.array(embedding).astype('float32')
            query_vec = query_vec / np.linalg.norm(query_vec)
            query_vec = query_vec.reshape(1, -1)

            # Step 3: Reconstruct vectors for BM25 candidates and rerank
            candidate_vectors = []
            for idx in top_bm25_indices[:self.rerank_top_k]:
                vec = self.index.reconstruct(int(idx))
                candidate_vectors.append(vec)

            candidate_matrix = np.array(candidate_vectors).astype('float32')
            similarities = np.dot(candidate_matrix, query_vec.T).flatten()

            # Step 4: Get top-k final results
            reranked_indices = np.argsort(similarities)[-self.final_top_k:][::-1]

            results = []
            for pos in reranked_indices:
                original_idx = top_bm25_indices[pos]
                meta = self.metadata[original_idx]

                # Extract book name (clean up filename)
                book_name = meta.get("book_name", "Unknown")
                if book_name != "Unknown":
                    # Shorten long book names
                    book_name = book_name.replace("_", " ")
                    if len(book_name) > 60:
                        book_name = book_name[:60] + "..."

                # Create page reference from chapter info
                chapter = meta.get("chapter_number")
                chapter_title = meta.get("chapter_title", "")
                if chapter:
                    page_ref = f"Ch. {chapter}"
                elif chapter_title and chapter_title != "pre-ch1":
                    page_ref = chapter_title
                else:
                    page_ref = "Intro"

                results.append({
                    "text": meta.get("text", ""),
                    "book": book_name,
                    "page": page_ref,
                    "score": float(similarities[pos]),
                    "chunk_id": meta.get("chunk_id", str(original_idx))
                })

            logger.info(f"Retrieved {len(results)} sources for query: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            return []


# Singleton instance
_retriever: HybridRAGRetriever | None = None


def get_rag_retriever() -> HybridRAGRetriever:
    """Get or create singleton retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRAGRetriever()
    return _retriever
