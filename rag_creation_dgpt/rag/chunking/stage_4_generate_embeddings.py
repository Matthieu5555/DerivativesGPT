"""
Stage 4: Embedding Generation and Index Population

This script completes the vector store by:
1. Loading vector store structure from Stage 3
2. Generating embeddings using Gemini API with checkpointing
3. Normalizing embeddings for cosine similarity
4. Adding embeddings to FAISS index
5. Saving completed vector store

The output is a fully functional RAG index ready for querying.
Called by: User runs after validating Stage 3 output
Dependencies: Stage 3 output files, GEMINI_API_KEY environment variable
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
import faiss
import google.generativeai as genai
from tqdm import tqdm

from config import PathConfig, GeminiConfig, VectorStoreConfig


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# CHECKPOINT CONFIGURATION
# Saves embeddings every N chunks to enable resume on failure
CHECKPOINT_INTERVAL = 500
CHECKPOINT_FILE = PathConfig.VECTORSTORE_DIR / "embeddings_checkpoint.npz"


def validate_gemini_config() -> None:
    """
    Validate Gemini API configuration before starting.
    
    Raises:
        ValueError: If API key not found or invalid
        
    Note:
        Called by: main() before any embedding generation
        Fails fast to avoid wasting time on unconfigured API
    """
    if not GeminiConfig.validate():
        raise ValueError(
            "GEMINI_API_KEY environment variable not set.\n"
            "Get your key from: https://aistudio.google.com/app/apikey\n"
            "Then set it in .env file or: export GEMINI_API_KEY='your-key-here'"
        )
    
    genai.configure(api_key=GeminiConfig.API_KEY)
    logger.info("Gemini API client configured successfully")


def test_gemini_connection() -> bool:
    """
    Test Gemini API with a single embedding request.
    
    Returns:
        True if connection successful, False otherwise
        
    Note:
        Called by: main() after configuration
        Catches API errors early before processing thousands of chunks
        CRITICAL: Validates embedding dimension is correct (768 for text-embedding-004)
    """
    try:
        result = genai.embed_content(
            model=GeminiConfig.EMBEDDING_MODEL,
            content=["test connection"],
            task_type=GeminiConfig.EMBEDDING_TASK_TYPE_DOCUMENT,
        )
        
        # Parse response correctly
        # result['embedding'] is a list of embeddings (one per input text)
        # Each embedding is a list of floats
        embeddings = result['embedding']
        
        if not embeddings or len(embeddings) == 0:
            logger.error("Gemini API returned empty embeddings")
            return False
        
        # Get first embedding
        first_embedding = embeddings[0]
        embedding_dim = len(first_embedding)
        
        # Verify dimension matches config
        if embedding_dim != VectorStoreConfig.EMBEDDING_DIMENSION:
            logger.error(
                f"CRITICAL: Embedding dimension mismatch!\n"
                f"Expected: {VectorStoreConfig.EMBEDDING_DIMENSION}\n"
                f"Got: {embedding_dim}\n"
                f"Check VectorStoreConfig.EMBEDDING_DIMENSION in config.py"
            )
            return False
        
        logger.info(
            f"Gemini API test successful. Embedding dimension: {embedding_dim} ✓"
        )
        return True
        
    except Exception as e:
        logger.error(f"Gemini API test failed: {e}")
        return False


def load_faiss_index(index_path: Path) -> faiss.Index:
    """
    Load empty FAISS index structure from Stage 3.
    
    Args:
        index_path: Path to FAISS index file
        
    Returns:
        Empty FAISS IndexFlatIP
        
    Raises:
        FileNotFoundError: If index file not found
        
    Note:
        Called by: load_vectorstore_structure()
        Separated for single responsibility
    """
    if not index_path.exists():
        raise FileNotFoundError(
            f"Index file not found: {index_path}\n"
            "Please run stage_3_create_vectorstore.py first"
        )
    
    index = faiss.read_index(str(index_path))
    logger.info(f"Loaded FAISS index structure from {index_path}")
    
    return index


def load_metadata_json(metadata_path: Path) -> list[dict]:
    """
    Load metadata from JSON file (not pickle).
    
    Args:
        metadata_path: Path to metadata JSON file
        
    Returns:
        List of chunk metadata dicts
        
    Raises:
        FileNotFoundError: If metadata file not found
        
    Note:
        Called by: load_vectorstore_structure()
        Stage 3 outputs JSON, not pickle
    """
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {metadata_path}\n"
            "Please run stage_3_create_vectorstore.py first"
        )
    
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    logger.info(f"Loaded metadata for {len(metadata)} chunks from {metadata_path}")
    
    return metadata


def load_vectorstore_structure() -> tuple[faiss.Index, list[dict]]:
    """
    Load empty FAISS index structure and metadata from Stage 3.
    
    Returns:
        Tuple of (FAISS index, metadata list)
        
    Note:
        Called by: main() to load structure before adding embeddings
        Orchestrates: load_faiss_index, load_metadata_json
    """
    index_path = PathConfig.STAGE_3_OUTPUT_DIR / "vectorstore_structure.faiss"
    metadata_path = PathConfig.STAGE_3_OUTPUT_DIR / "metadata_structure.json"
    
    index = load_faiss_index(index_path)
    metadata = load_metadata_json(metadata_path)
    
    return index, metadata


def prepare_text_for_embedding(chunk_metadata: dict) -> str:
    """
    Prepare text for embedding by combining hierarchical context with content.
    
    Combines (in hierarchical order):
    - Book name (highest level - which book this is from)
    - Chapter summary (mid level - chapter context)
    - Actual chunk text (lowest level - specific content)
    
    This complete hierarchy helps embeddings capture:
    - Semantic meaning (what the text says)
    - Structural context (where it sits in the book)
    - Source context (which domain/book it comes from)
    
    Args:
        chunk_metadata: Single chunk metadata dict
        
    Returns:
        Combined text string ready for embedding
        
    Note:
        Called by: extract_texts_from_metadata() for each chunk
        Format designed to give LLM complete hierarchical understanding
        Helps distinguish similar content from different books
    """
    book_name = chunk_metadata.get("book_name", "")
    chapter_summary = chunk_metadata.get("chapter_summary", "")
    text = chunk_metadata.get("text", "")
    
    # Format: highest context -> mid context -> specific content
    # This hierarchical structure helps the model understand both WHAT and WHERE
    combined = f"Book: {book_name}\n\nChapter Context: {chapter_summary}\n\nContent: {text}"
    
    return combined


def extract_texts_from_metadata(metadata: list[dict]) -> list[str]:
    """
    Extract and prepare texts from metadata for embedding.
    
    Args:
        metadata: List of chunk metadata dicts
        
    Returns:
        List of prepared text strings in same order as metadata
        
    Note:
        Called by: main() to prepare texts for embedding
        Preserves order to match embeddings with metadata
        Uses prepare_text_for_embedding to combine context + content
    """
    texts = [prepare_text_for_embedding(m) for m in metadata]
    logger.info(f"Prepared {len(texts)} texts for embedding")
    
    return texts


def generate_embeddings_batch(texts: list[str], retry_count: int = 3) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts using Gemini API with retries.
    
    CRITICAL: Properly parses Gemini API response format.
    Response structure: {'embedding': [[float, float, ...], [float, float, ...], ...]}
    Each element in 'embedding' list is one embedding vector.
    
    Args:
        texts: List of text strings to embed (up to EMBEDDING_BATCH_SIZE)
        retry_count: Number of retries on failure
        
    Returns:
        List of embedding vectors (each is list of floats)
        
    Raises:
        Exception: If all retries fail
        
    Note:
        Called by: generate_embeddings_with_checkpointing() for each batch
        Uses exponential backoff on retries
        Single API call per batch (cost-efficient)
    """
    for attempt in range(retry_count):
        try:
            result = genai.embed_content(
                model=GeminiConfig.EMBEDDING_MODEL,
                content=texts,
                task_type=GeminiConfig.EMBEDDING_TASK_TYPE_DOCUMENT,
            )
            
            # CRITICAL: Correct response parsing
            # result['embedding'] is a list where each element is an embedding
            # For batch of N texts, we get N embeddings
            embeddings = result['embedding']
            
            # Validate we got the right number of embeddings
            if len(embeddings) != len(texts):
                raise ValueError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                )
            
            # Validate embedding dimensions
            for i, emb in enumerate(embeddings):
                if len(emb) != VectorStoreConfig.EMBEDDING_DIMENSION:
                    raise ValueError(
                        f"Embedding {i} has dimension {len(emb)}, "
                        f"expected {VectorStoreConfig.EMBEDDING_DIMENSION}"
                    )
            
            return embeddings
            
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Embedding batch failed (attempt {attempt + 1}/{retry_count}): {e}\n"
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Embedding batch failed after {retry_count} attempts: {e}")
                raise


def save_checkpoint(embeddings_so_far: np.ndarray, last_index: int) -> None:
    """
    Save embedding checkpoint to enable resume on failure.
    
    Args:
        embeddings_so_far: Embeddings generated up to this point
        last_index: Index of last successfully embedded chunk
        
    Note:
        Called by: generate_embeddings_with_checkpointing() periodically
        Checkpoint file stores embeddings + metadata about progress
    """
    np.savez(
        CHECKPOINT_FILE,
        embeddings=embeddings_so_far,
        last_index=last_index,
    )
    logger.info(f"Checkpoint saved at chunk {last_index + 1}")


def load_checkpoint() -> Optional[tuple[np.ndarray, int]]:
    """
    Load checkpoint if it exists.
    
    Returns:
        Tuple of (embeddings, last_index) if checkpoint exists, None otherwise
        
    Note:
        Called by: generate_embeddings_with_checkpointing() at start
        Enables resuming from where we left off on failure
    """
    if not CHECKPOINT_FILE.exists():
        return None
    
    try:
        data = np.load(CHECKPOINT_FILE)
        embeddings = data["embeddings"]
        last_index = int(data["last_index"])
        
        logger.info(
            f"Found checkpoint at chunk {last_index + 1}. "
            f"Resuming from there..."
        )
        
        return embeddings, last_index
        
    except Exception as e:
        logger.warning(f"Failed to load checkpoint: {e}. Starting fresh.")
        return None


def delete_checkpoint() -> None:
    """
    Delete checkpoint file after successful completion.
    
    Note:
        Called by: generate_embeddings_with_checkpointing() on success
        Cleanup to avoid confusion in future runs
    """
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        logger.info("Checkpoint file deleted")


def generate_embeddings_with_checkpointing(texts: list[str]) -> np.ndarray:
    """
    Generate embeddings for all texts with checkpointing and progress tracking.
    
    Features:
    - Batch processing for efficiency
    - Checkpointing every N chunks for recovery
    - Progress bar for user feedback
    - Rate limiting with delays between batches
    - Resume from checkpoint if available
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        NumPy array of embeddings (shape: [num_texts, embedding_dim])
        
    Note:
        Called by: main() after loading texts
        Orchestrates: load_checkpoint, generate_embeddings_batch, save_checkpoint
        This is the main embedding generation loop
    """
    # Try to resume from checkpoint
    checkpoint_data = load_checkpoint()
    
    if checkpoint_data is not None:
        embeddings_list = checkpoint_data[0].tolist()
        start_index = checkpoint_data[1] + 1
        logger.info(f"Resuming from chunk {start_index}")
    else:
        embeddings_list = []
        start_index = 0
        logger.info("Starting fresh embedding generation")
    
    logger.info(f"Generating embeddings for {len(texts)} chunks...")
    logger.info(f"Batch size: {VectorStoreConfig.EMBEDDING_BATCH_SIZE}")
    logger.info(f"Model: {GeminiConfig.EMBEDDING_MODEL}")
    logger.info(f"Checkpointing every {CHECKPOINT_INTERVAL} chunks")
    
    # Process in batches
    batch_size = VectorStoreConfig.EMBEDDING_BATCH_SIZE
    
    for i in tqdm(
        range(start_index, len(texts), batch_size),
        desc="Embedding batches",
        initial=start_index // batch_size,
        total=(len(texts) + batch_size - 1) // batch_size,
    ):
        batch = texts[i : i + batch_size]
        
        batch_embeddings = generate_embeddings_batch(batch)
        embeddings_list.extend(batch_embeddings)
        
        # Save checkpoint periodically
        if (i + batch_size) % CHECKPOINT_INTERVAL == 0 or (i + batch_size) >= len(texts):
            embeddings_array = np.array(embeddings_list, dtype="float32")
            save_checkpoint(embeddings_array, i + len(batch) - 1)
        
        # Rate limiting: delay between batches (except last one)
        if i + batch_size < len(texts):
            time.sleep(VectorStoreConfig.BATCH_DELAY)
    
    embeddings_array = np.array(embeddings_list, dtype="float32")
    logger.info(f"Generated embeddings with shape: {embeddings_array.shape}")
    
    # Delete checkpoint on successful completion
    delete_checkpoint()
    
    return embeddings_array


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """
    Normalize embeddings to unit length for cosine similarity.
    
    CRITICAL: This must be done for IndexFlatIP to work as cosine similarity.
    Cosine similarity = inner product of normalized vectors.
    
    Args:
        embeddings: Raw embedding vectors
        
    Returns:
        Normalized embedding vectors (each has L2 norm = 1)
        
    Note:
        Called by: main() after generating embeddings
        Without this, IndexFlatIP would compute regular inner product, not cosine
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    
    # Avoid division by zero (shouldn't happen with real embeddings)
    norms = np.where(norms == 0, 1, norms)
    
    normalized = embeddings / norms
    
    # Verify normalization
    normalized_norms = np.linalg.norm(normalized, axis=1)
    min_norm = np.min(normalized_norms)
    max_norm = np.max(normalized_norms)
    
    logger.info("Normalized embeddings for cosine similarity")
    logger.info(
        f"Normalized embedding norms (should all be ~1.0): "
        f"min={min_norm:.4f}, max={max_norm:.4f}"
    )
    
    # Warn if normalization seems wrong
    if min_norm < 0.99 or max_norm > 1.01:
        logger.warning(
            f"Normalization produced unexpected norms! "
            f"Expected ~1.0, got range [{min_norm:.4f}, {max_norm:.4f}]"
        )
    
    return normalized


def verify_embeddings_dimension(embeddings: np.ndarray, expected_dim: int) -> None:
    """
    Verify embeddings have expected dimension.
    
    Args:
        embeddings: Generated embeddings
        expected_dim: Expected dimension (should match FAISS index)
        
    Raises:
        ValueError: If dimension mismatch
        
    Note:
        Called by: main() before adding to index
        Catches dimension mismatches early
    """
    actual_dim = embeddings.shape[1]
    
    if actual_dim != expected_dim:
        raise ValueError(
            f"Embedding dimension mismatch!\n"
            f"Expected: {expected_dim} (from config)\n"
            f"Actual: {actual_dim} (from Gemini API)\n"
            f"Check VectorStoreConfig.EMBEDDING_DIMENSION"
        )
    
    logger.info(f"Embedding dimension verified: {actual_dim} ✓")


def populate_faiss_index(index: faiss.Index, embeddings: np.ndarray) -> faiss.Index:
    """
    Add normalized embeddings to FAISS index.
    
    Args:
        index: Empty FAISS IndexFlatIP from Stage 3
        embeddings: Normalized embedding vectors
        
    Returns:
        Populated FAISS index
        
    Note:
        Called by: main() after generating and normalizing embeddings
        This completes the vector store creation
    """
    index.add(embeddings)
    logger.info(f"Added {embeddings.shape[0]} vectors to FAISS index")
    logger.info(f"Index now contains {index.ntotal} vectors")
    
    return index


def save_faiss_index(index: faiss.Index, output_path: Path) -> None:
    """
    Save completed FAISS index to disk.
    
    Args:
        index: Populated FAISS index
        output_path: Path where index will be saved
        
    Note:
        Called by: save_completed_vectorstore()
        Separated for single responsibility
    """
    faiss.write_index(index, str(output_path))
    logger.info(f"Saved completed index to {output_path}")


def save_metadata_json(metadata: list[dict], output_path: Path) -> None:
    """
    Save metadata to final location as JSON.
    
    Args:
        metadata: Chunk metadata
        output_path: Path where metadata will be saved
        
    Note:
        Called by: save_completed_vectorstore()
        Uses JSON for portability and readability
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved metadata to {output_path}")


def save_completed_vectorstore(
    index: faiss.Index, metadata: list[dict], output_dir: Path
) -> None:
    """
    Save completed vector store to final location.
    
    Args:
        index: Populated FAISS index
        metadata: Chunk metadata
        output_dir: Final output directory
        
    Note:
        Called by: main() after populating index
        These files are used by the query script
    """
    index_path = output_dir / "rag_index_structured.faiss"
    metadata_path = output_dir / "metadata_structured.json"
    
    save_faiss_index(index, index_path)
    save_metadata_json(metadata, metadata_path)


def calculate_completion_metrics(
    index: faiss.Index, metadata: list[dict], embeddings: np.ndarray
) -> dict:
    """
    Calculate final completion metrics.
    
    Args:
        index: Completed FAISS index
        metadata: All chunk metadata
        embeddings: All embedding vectors
        
    Returns:
        Dict with completion metrics
        
    Note:
        Called by: generate_completion_report()
        Pure function with no side effects
    """
    unique_books = len(set(m["book_name"] for m in metadata))
    
    # Check embedding quality
    norms = np.linalg.norm(embeddings, axis=1)
    avg_norm = float(np.mean(norms))
    
    return {
        "total_chunks": len(metadata),
        "total_vectors": index.ntotal,
        "embedding_dimension": embeddings.shape[1],
        "unique_books": unique_books,
        "avg_embedding_norm": avg_norm,
        "embeddings_normalized": 0.99 <= avg_norm <= 1.01,  # Should be ~1.0
    }


def generate_completion_report(
    index: faiss.Index, metadata: list[dict], embeddings: np.ndarray
) -> dict:
    """
    Create final summary statistics for completed vector store.
    
    Args:
        index: Completed FAISS index
        metadata: All chunk metadata
        embeddings: All embedding vectors
        
    Returns:
        Dict with completion metrics
        
    Note:
        Called by: main() to provide final validation info
    """
    metrics = calculate_completion_metrics(index, metadata, embeddings)
    
    return {
        **metrics,
        "index_type": "IndexFlatIP",
        "similarity_metric": "cosine",
        "embedding_model": GeminiConfig.EMBEDDING_MODEL,
        "vector_store_complete": True,
        "ready_for_queries": True,
    }


def save_completion_report(report: dict, output_path: Path) -> None:
    """
    Save completion report as JSON.
    
    Args:
        report: Completion metrics dict
        output_path: Path where report will be saved
        
    Note:
        Called by: main() to document final vector store state
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Completion report saved to {output_path}")


def log_completion_summary(report: dict) -> None:
    """
    Log completion summary to console.
    
    Args:
        report: Completion metrics dict
        
    Note:
        Called by: main() to show summary
        Pure logging function
    """
    logger.info(f"\nTotal vectors indexed: {report['total_vectors']}")
    logger.info(f"Embedding dimension: {report['embedding_dimension']}")
    logger.info(f"Books indexed: {report['unique_books']}")
    logger.info(f"Embedding model: {report['embedding_model']}")
    logger.info(f"Embeddings normalized: {report['embeddings_normalized']}")
    logger.info(f"Average norm: {report['avg_embedding_norm']:.4f} (should be ~1.0)")


def main() -> None:
    """
    Main orchestration function for Stage 4.
    
    Coordinates:
    1. Ensuring output directories exist
    2. Validating and testing Gemini API
    3. Loading vector store structure
    4. Generating embeddings with checkpointing
    5. Normalizing embeddings for cosine similarity
    6. Verifying embedding dimension
    7. Populating FAISS index
    8. Saving completed vector store
    9. Generating completion report
    
    Note:
        This is the final stage. After completion, query_rag_index.py can be used.
        Embedding generation uses checkpointing to enable resume on failure.
    """
    logger.info("=" * 80)
    logger.info("STAGE 4: EMBEDDING GENERATION AND INDEX POPULATION")
    logger.info("=" * 80)
    
    PathConfig.ensure_directories()
    
    # Validate Gemini API configuration
    try:
        validate_gemini_config()
    except ValueError as e:
        logger.error(str(e))
        return
    
    # Test Gemini API connection with dimension validation
    if not test_gemini_connection():
        logger.error(
            "Gemini API test failed. Please check:\n"
            "1. Your API key is correct\n"
            "2. Network connection is working\n"
            "3. VectorStoreConfig.EMBEDDING_DIMENSION matches model output"
        )
        return
    
    # Load vector store structure from Stage 3
    try:
        index, metadata = load_vectorstore_structure()
    except FileNotFoundError as e:
        logger.error(str(e))
        return
    
    # Prepare texts for embedding
    texts = extract_texts_from_metadata(metadata)
    
    # Generate embeddings with checkpointing
    embeddings = generate_embeddings_with_checkpointing(texts)
    
    # Verify count matches
    if embeddings.shape[0] != len(metadata):
        logger.error(
            f"Embedding count mismatch: {embeddings.shape[0]} embeddings "
            f"vs {len(metadata)} chunks"
        )
        return
    
    # CRITICAL: Normalize embeddings for cosine similarity
    embeddings = normalize_embeddings(embeddings)
    
    # Verify dimension matches index
    try:
        verify_embeddings_dimension(embeddings, VectorStoreConfig.EMBEDDING_DIMENSION)
    except ValueError as e:
        logger.error(str(e))
        return
    
    # Add to FAISS index
    index = populate_faiss_index(index, embeddings)
    
    # Save completed vector store
    save_completed_vectorstore(index, metadata, PathConfig.VECTORSTORE_DIR)
    
    # Generate and save completion report
    report = generate_completion_report(index, metadata, embeddings)
    report_path = PathConfig.VECTORSTORE_DIR / "completion_report.json"
    save_completion_report(report, report_path)
    
    logger.info("\n" + "=" * 80)
    logger.info("STAGE 4 COMPLETE - VECTOR STORE READY")
    logger.info("=" * 80)
    
    log_completion_summary(report)
    
    logger.info(f"\nOutput directory: {PathConfig.VECTORSTORE_DIR}")
    logger.info("\nYour RAG system is ready!")
    logger.info("\nNext steps:")
    logger.info("1. Test queries with: python query_rag_index.py")
    logger.info("2. Review completion_report.json for final metrics")
    logger.info("3. Verify embeddings_normalized: True in report")


if __name__ == "__main__":
    main()