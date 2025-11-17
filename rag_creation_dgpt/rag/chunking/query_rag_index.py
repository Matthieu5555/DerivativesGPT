"""
Query Interface for 4-Stage RAG Pipeline

Provides semantic search and answer generation using the completed vector store.
This script works with the final output from stage_4_generate_embeddings.py.

Usage:
    python query_rag_index.py              # Interactive mode
    python query_rag_index.py --examples   # Run example queries
"""

import argparse
import pickle
from pathlib import Path

import numpy as np
import faiss
import google.generativeai as genai

from config import PathConfig, GeminiConfig, QueryConfig


def init_gemini_client() -> None:
    """
    Initialize Gemini API client.
    
    Note:
        Called by: main() before any queries
        Required for both embedding queries and generating answers
    """
    if not GeminiConfig.validate():
        raise ValueError(
            "GEMINI_API_KEY environment variable not set. "
            "Please set it before running queries."
        )
        
    genai.configure(api_key=GeminiConfig.API_KEY)
    print(f"✓ Gemini API client initialized")


def load_index() -> tuple[faiss.Index, list[dict]]:
    """
    Load completed FAISS index and metadata.
    
    Returns:
        Tuple of (FAISS index, metadata list)
        
    Note:
        Called by: main() to load the vector store
        Expects files created by stage_4_generate_embeddings.py
    """
    index_path = PathConfig.VECTORSTORE_DIR / "rag_index_structured.faiss"
    metadata_path = PathConfig.VECTORSTORE_DIR / "metadata_structured.pkl"

    if not index_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Vector store not found in {PathConfig.VECTORSTORE_DIR}. "
            "Please complete all 4 pipeline stages first."
        )

    index = faiss.read_index(str(index_path))

    with open(metadata_path, "rb") as f:
        metadata = pickle.load(f)

    print(f"✓ Loaded index with {index.ntotal} vectors")
    return index, metadata


def embed_query(query: str) -> np.ndarray:
    """
    Generate embedding for search query.
    
    Args:
        query: User's search query
        
    Returns:
        Query embedding as NumPy array
        
    Note:
        Called by: search_index() to convert query to vector
        Uses same embedding model as indexing but with RETRIEVAL_QUERY task type
    """
    result = genai.embed_content(
        model=GeminiConfig.EMBEDDING_MODEL,
        content=query,
        task_type=GeminiConfig.EMBEDDING_TASK_TYPE_QUERY,
    )
    
    if isinstance(result, dict) and "embedding" in result:
        embedding = result["embedding"]
    else:
        embedding = result["embeddings"][0]["values"] if isinstance(result["embeddings"][0], dict) else result["embeddings"][0]
    
    return np.array([embedding], dtype="float32")


def search_index(
    query: str,
    index: faiss.Index,
    metadata: list[dict],
    top_k: int = QueryConfig.TOP_K,
    chapter_filter: str = None,
) -> list[dict]:
    """
    Search vector store for relevant chunks.
    
    Args:
        query: Search query string
        index: FAISS index
        metadata: Chunk metadata list
        top_k: Number of results to return
        chapter_filter: Optional chapter name to filter results
        
    Returns:
        List of metadata dicts with added 'score' field
        
    Note:
        Called by: interactive_query() and run_examples()
        Implements semantic search with optional chapter filtering
    """
    query_vector = embed_query(query)

    distances, indices = index.search(query_vector, top_k * 2)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        meta = metadata[idx].copy()
        meta["score"] = float(dist)

        if chapter_filter and chapter_filter.lower() not in meta["chapter"].lower():
            continue

        results.append(meta)

        if len(results) >= top_k:
            break

    return results


def generate_answer(query: str, context_chunks: list[dict]) -> str:
    """
    Generate answer using retrieved chunks and Gemini.
    
    Args:
        query: User's question
        context_chunks: Retrieved chunks from search
        
    Returns:
        Generated answer with citations
        
    Note:
        Called by: interactive_query() when user requests full answer
        Combines chunk context and prompts Gemini for synthesis
    """
    model = genai.GenerativeModel(GeminiConfig.GENERATION_MODEL)

    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        chapter = chunk["chapter"]
        section = chunk.get("section", "")
        text = chunk["text"][:500]

        context_parts.append(f"[Source {i}: {chapter} - {section}]\n{text}\n")

    context = "\n\n".join(context_parts)

    prompt = f"""Answer the question based on the provided context from academic textbooks.
Cite specific sources when making claims (e.g., "According to Source 2...").

Context:
{context}

Question: {query}

Answer:"""

    response = model.generate_content(prompt)
    return response.text if response.text else "Unable to generate answer."


def display_results(query: str, results: list[dict], show_text: bool = False) -> None:
    """
    Display search results in readable format.
    
    Args:
        query: The search query
        results: List of result metadata
        show_text: Whether to show chunk text preview
        
    Note:
        Called by: interactive_query() to format output for user
    """
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")

    if not results:
        print("No results found.")
        return

    for i, result in enumerate(results, 1):
        print(f"Result {i} (score: {result['score']:.4f})")
        print(f"  Source: {result['source']}")
        print(f"  Chapter: {result['chapter']}")
        print(f"  Section: {result.get('section', 'N/A')}")
        print(f"  Summary: {result['chapter_summary'][:100]}...")

        if show_text:
            print(f"  Text: {result['text'][:200]}...")

        print()


def interactive_query(index: faiss.Index, metadata: list[dict]) -> None:
    """
    Interactive query loop for testing.
    
    Args:
        index: FAISS index
        metadata: Chunk metadata list
        
    Note:
        Called by: main() when running in interactive mode
        Provides commands for exploration and querying
    """
    print("\n" + "="*80)
    print("Interactive RAG Query Interface")
    print("="*80)
    print("\nCommands:")
    print("  - Enter a question to search")
    print("  - Type 'chapters' to see available chapters")
    print("  - Type 'sources' to see available sources")
    print("  - Type 'quit' to exit\n")

    while True:
        query = input("\nQuery: ").strip()

        if not query:
            continue

        if query.lower() == "quit":
            break

        if query.lower() == "chapters":
            chapters = sorted(set(m["chapter"] for m in metadata))
            print("\nAvailable chapters:")
            for ch in chapters:
                print(f"  - {ch}")
            continue

        if query.lower() == "sources":
            sources = sorted(set(m["source"] for m in metadata))
            print("\nAvailable sources:")
            for src in sources:
                count = sum(1 for m in metadata if m["source"] == src)
                print(f"  - {src} ({count} chunks)")
            continue

        try:
            results = search_index(query, index, metadata)
            display_results(query, results, show_text=True)

            gen_answer = input("\nGenerate full answer? (y/n): ").strip().lower()
            if gen_answer == "y":
                answer = generate_answer(query, results)
                print(f"\nGenerated Answer:\n{answer}")
                print("\nSources used:")
                for i, r in enumerate(results, 1):
                    print(f"  {i}. {r['chapter']} - {r.get('section', 'N/A')}")

        except Exception as e:
            print(f"Error: {e}")


def run_examples(index: faiss.Index, metadata: list[dict]) -> None:
    """
    Run example queries to demonstrate functionality.
    
    Args:
        index: FAISS index
        metadata: Chunk metadata list
        
    Note:
        Called by: main() when --examples flag is used
        Demonstrates basic search, filtered search, and answer generation
    """
    print("\n" + "="*80)
    print("EXAMPLE QUERIES")
    print("="*80)

    query1 = "What is portfolio optimization?"
    print(f"\n{'#'*80}")
    print("Example 1: Basic Semantic Search")
    print(f"{'#'*80}")
    results1 = search_index(query1, index, metadata)
    display_results(query1, results1)

    if not results1:
        print("No results found. This may indicate indexing issues.")
        return

    query2 = "risk measures"
    chapter = "Chapter 3"
    print(f"\n{'#'*80}")
    print("Example 2: Chapter-Filtered Search")
    print(f"{'#'*80}")
    results2 = search_index(query2, index, metadata, chapter_filter=chapter)
    display_results(query2, results2)

    query3 = "Explain the efficient frontier"
    print(f"\n{'#'*80}")
    print("Example 3: RAG-based Answer Generation")
    print(f"{'#'*80}")
    results3 = search_index(query3, index, metadata)
    answer = generate_answer(query3, results3)

    print(f"\nQuestion: {query3}")
    print(f"\nAnswer:\n{answer}")
    print("\nSources used:")
    for i, r in enumerate(results3, 1):
        print(f"  {i}. {r['chapter']} - {r.get('section', 'N/A')}")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
        
    Note:
        Called by: main() to determine run mode
    """
    parser = argparse.ArgumentParser(
        description="Query the structured RAG index"
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Run example queries instead of interactive mode",
    )
    return parser.parse_args()


def main() -> None:
    """
    Main entry point for query interface.
    
    Coordinates:
    1. Initializing Gemini client
    2. Loading vector store
    3. Running either interactive or example mode
    
    Note:
        Run with --examples flag to see demonstrations
        Run without flags for interactive querying
    """
    args = parse_arguments()

    print("="*80)
    print("RAG QUERY INTERFACE")
    print("="*80)

    try:
        init_gemini_client()
    except ValueError as e:
        print(f"\nError: {e}")
        return

    try:
        index, metadata = load_index()
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease complete the 4-stage pipeline first:")
        print("  1. python stage_1_basic_chunking.py")
        print("  2. python stage_2_augment_chunks.py")
        print("  3. python stage_3_create_vectorstore.py")
        print("  4. python stage_4_generate_embeddings.py")
        return

    if args.examples:
        run_examples(index, metadata)
    else:
        interactive_query(index, metadata)


if __name__ == "__main__":
    main()
