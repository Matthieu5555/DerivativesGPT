"""
Stage 3: Vector Store Creation

This script creates the FAISS vector store structure by:
1. Loading augmented chunks from Stage 2
2. Validating schema matches expectations
3. Preparing metadata for each chunk
4. Creating FAISS index structure (IndexFlatIP for cosine similarity)
5. Saving metadata as JSON

The output is a vector store structure ready for embedding generation.
Called by: User runs after validating Stage 2 output
Dependencies: Stage 2 output files
"""

import json
import logging
from pathlib import Path
from typing import Any

import faiss

from config import PathConfig, VectorStoreConfig


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# EXPECTED SCHEMA FROM STAGE 2
# This defines what fields we expect from Stage 2 output
EXPECTED_CHUNK_SCHEMA = {
    "chunk_id": str,
    "book_name": str,
    "chapter_number": (int, type(None)),
    "chapter_title": str,
    "chunk_index_in_chapter": int,
    "total_chunks_in_chapter": int,
    "text": str,
    "char_start": int,
    "char_end": int,
    "chunking_method": str,
    "confidence": float,
    "position_percent": float,
    "chapter_summary": str,
}


def validate_chunk_schema(chunk: dict) -> tuple[bool, str]:
    """
    Validate that a chunk matches expected schema from Stage 2.
    
    Args:
        chunk: Chunk dict from Stage 2 output
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Note:
        Called by: load_augmented_chunks() for each chunk
        This prevents schema mismatches from causing runtime failures
    """
    for field, expected_type in EXPECTED_CHUNK_SCHEMA.items():
        if field not in chunk:
            return False, f"Missing required field: {field}"
        
        if isinstance(expected_type, tuple):
            if not isinstance(chunk[field], expected_type):
                return False, f"Field {field} has wrong type: {type(chunk[field])} (expected {expected_type})"
        else:
            if not isinstance(chunk[field], expected_type):
                return False, f"Field {field} has wrong type: {type(chunk[field])} (expected {expected_type})"
    
    return True, ""


def load_augmented_chunks(filepath: Path) -> list[dict]:
    """
    Load and validate augmented chunks from Stage 2 JSON output.
    
    Args:
        filepath: Path to Stage 2 output JSON file
        
    Returns:
        List of validated chunk dicts with chapter summaries
        
    Raises:
        ValueError: If schema validation fails for any chunk
        
    Note:
        Called by: prepare_vectorstore_data() to load all chunks
        Validates schema to catch mismatches early
    """
    with open(filepath, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # Validate first chunk to catch schema issues early
    if chunks:
        is_valid, error_msg = validate_chunk_schema(chunks[0])
        if not is_valid:
            raise ValueError(
                f"Schema validation failed for {filepath.name}: {error_msg}\n"
                "Stage 2 output schema does not match expectations."
            )

    logger.info(f"Loaded {len(chunks)} augmented chunks from {filepath.name}")
    return chunks


def prepare_chunk_metadata(chunk: dict) -> dict:
    """
    Convert chunk dict to metadata format for vector store.
    
    Uses actual Stage 2 output schema:
    - book_name (not "source")
    - chapter_number (not "chapter")
    - chapter_title (not "section")
    
    Args:
        chunk: Augmented chunk dict from Stage 2
        
    Returns:
        Metadata dict with all relevant fields
        
    Note:
        Called by: prepare_vectorstore_data() for each chunk
        This metadata will be stored alongside embeddings
        Keep all Stage 2 fields for maximum flexibility in retrieval
    """
    return {
        "chunk_id": chunk["chunk_id"],
        "book_name": chunk["book_name"],
        "chapter_number": chunk["chapter_number"],
        "chapter_title": chunk["chapter_title"],
        "chunk_index_in_chapter": chunk["chunk_index_in_chapter"],
        "total_chunks_in_chapter": chunk["total_chunks_in_chapter"],
        "text": chunk["text"],
        "chapter_summary": chunk["chapter_summary"],
        "chunking_method": chunk["chunking_method"],
        "confidence": chunk["confidence"],
        "position_percent": chunk["position_percent"],
    }


def load_all_chunks_from_stage2(input_dir: Path) -> list[dict]:
    """
    Load all augmented chunks from all Stage 2 output files.
    
    Args:
        input_dir: Directory containing Stage 2 output files
        
    Returns:
        List of all chunks from all files
        
    Raises:
        FileNotFoundError: If no Stage 2 output files found
        
    Note:
        Called by: prepare_vectorstore_data()
        Aggregates chunks from all books
    """
    input_files = sorted(input_dir.glob("*_augmented.json"))

    if not input_files:
        raise FileNotFoundError(
            f"No Stage 2 output files found in {input_dir}\n"
            "Expected files matching pattern: *_augmented.json\n"
            "Please run stage_2_augment_chunks.py first"
        )

    logger.info(f"Found {len(input_files)} Stage 2 output files")

    all_chunks = []
    for input_file in input_files:
        chunks = load_augmented_chunks(input_file)
        all_chunks.extend(chunks)

    logger.info(f"Loaded total of {len(all_chunks)} chunks from all files")
    return all_chunks


def convert_chunks_to_metadata(chunks: list[dict]) -> list[dict]:
    """
    Convert all chunks to metadata format.
    
    Args:
        chunks: List of chunk dicts from Stage 2
        
    Returns:
        List of metadata dicts
        
    Note:
        Called by: prepare_vectorstore_data()
        Pure transformation function with no side effects
    """
    return [prepare_chunk_metadata(chunk) for chunk in chunks]


def prepare_vectorstore_data() -> list[dict]:
    """
    Load and prepare all chunk metadata for vector store.
    
    Returns:
        List of metadata dicts ready for storage
        
    Note:
        Called by: main() to gather all chunks from all books
        Orchestrates: load_all_chunks_from_stage2, convert_chunks_to_metadata
    """
    all_chunks = load_all_chunks_from_stage2(PathConfig.STAGE_2_OUTPUT_DIR)
    all_metadata = convert_chunks_to_metadata(all_chunks)
    
    logger.info(f"Prepared metadata for {len(all_metadata)} chunks")
    return all_metadata


def create_empty_faiss_index(dimension: int) -> faiss.Index:
    """
    Create empty FAISS index structure for cosine similarity.
    
    IMPORTANT: Uses IndexFlatIP (Inner Product) not IndexFlatL2.
    Cosine similarity = inner product of normalized vectors.
    Embeddings MUST be normalized in Stage 4.
    
    Args:
        dimension: Embedding vector dimension
        
    Returns:
        Empty FAISS IndexFlatIP index
        
    Note:
        Called by: main() to initialize vector store structure
        IndexFlatIP performs exhaustive search (O(n) per query)
        Fine for ~5k chunks, but consider IVF/HNSW for larger datasets
        Index will be populated with normalized embeddings in Stage 4
    """
    index = faiss.IndexFlatIP(dimension)
    logger.info(
        f"Created empty FAISS IndexFlatIP with dimension {dimension} "
        "(for cosine similarity with normalized vectors)"
    )
    return index


def save_index_structure(index: faiss.Index, output_path: Path) -> None:
    """
    Save empty FAISS index structure to disk.
    
    Args:
        index: Empty FAISS index
        output_path: Path where index will be saved
        
    Note:
        Called by: save_vectorstore_structure()
        Separated for single responsibility
    """
    faiss.write_index(index, str(output_path))
    logger.info(f"Saved index structure to {output_path}")


def save_metadata_json(metadata: list[dict], output_path: Path) -> None:
    """
    Save metadata as JSON (not pickle).
    
    JSON advantages over pickle:
    - Human-readable for debugging
    - Portable across Python versions
    - No security risks
    - Can be inspected with standard tools
    
    Args:
        metadata: List of chunk metadata dicts
        output_path: Path where metadata will be saved
        
    Note:
        Called by: save_vectorstore_structure()
        Uses indent=2 for readability
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved metadata to {output_path}")


def save_vectorstore_structure(
    index: faiss.Index, metadata: list[dict], output_dir: Path
) -> None:
    """
    Save FAISS index structure and metadata to disk.
    
    Args:
        index: Empty FAISS index
        metadata: List of chunk metadata dicts
        output_dir: Directory where files will be saved
        
    Note:
        Called by: main() after creating structure
        Saves two files:
        - vectorstore_structure.faiss: Empty index structure
        - metadata_structure.json: All chunk metadata (JSON not pickle)
    """
    index_path = output_dir / "vectorstore_structure.faiss"
    metadata_path = output_dir / "metadata_structure.json"

    save_index_structure(index, index_path)
    save_metadata_json(metadata, metadata_path)


def calculate_unique_counts(metadata: list[dict]) -> dict[str, int]:
    """
    Calculate counts of unique entities in metadata.
    
    Args:
        metadata: List of chunk metadata
        
    Returns:
        Dict with counts of unique books, chapters, sections
        
    Note:
        Called by: generate_vectorstore_report()
        Pure function with no side effects
    """
    unique_books = len(set(m["book_name"] for m in metadata))
    
    # Count unique chapters (some chunks have chapter_number=None for gaps)
    unique_chapters = len(set(
        m["chapter_number"] 
        for m in metadata 
        if m["chapter_number"] is not None
    ))
    
    # Count unique (chapter, section) combinations
    unique_sections = len(set(
        f"{m['chapter_number']}:{m['chapter_title']}" 
        for m in metadata
    ))
    
    return {
        "unique_books": unique_books,
        "unique_chapters": unique_chapters,
        "unique_sections": unique_sections,
    }


def calculate_text_statistics(metadata: list[dict]) -> dict[str, float]:
    """
    Calculate statistics about text lengths.
    
    Args:
        metadata: List of chunk metadata
        
    Returns:
        Dict with text length statistics
        
    Note:
        Called by: generate_vectorstore_report()
        Pure function with no side effects
    """
    text_lengths = [len(m["text"]) for m in metadata]
    
    return {
        "avg_text_length": sum(text_lengths) / len(text_lengths) if text_lengths else 0,
        "min_text_length": min(text_lengths) if text_lengths else 0,
        "max_text_length": max(text_lengths) if text_lengths else 0,
    }


def count_chunks_by_book(metadata: list[dict]) -> dict[str, int]:
    """
    Count how many chunks exist for each book.
    
    Args:
        metadata: List of chunk metadata
        
    Returns:
        Dict mapping book names to chunk counts
        
    Note:
        Called by: generate_vectorstore_report()
        Pure function with no side effects
    """
    chunks_by_book = {}
    for m in metadata:
        book = m["book_name"]
        chunks_by_book[book] = chunks_by_book.get(book, 0) + 1
    
    return chunks_by_book


def generate_vectorstore_report(metadata: list[dict]) -> dict[str, Any]:
    """
    Create summary statistics for vector store validation.
    
    Args:
        metadata: All chunk metadata
        
    Returns:
        Dict with vector store metrics
        
    Note:
        Called by: main() to help users verify structure before embedding
        Composes multiple pure functions to build report
    """
    if not metadata:
        return {"error": "No metadata provided"}

    unique_counts = calculate_unique_counts(metadata)
    text_stats = calculate_text_statistics(metadata)
    chunks_by_book = count_chunks_by_book(metadata)

    return {
        "total_chunks": len(metadata),
        **unique_counts,
        **text_stats,
        "chunks_by_book": chunks_by_book,
        "index_type": "IndexFlatIP",
        "similarity_metric": "cosine (via inner product of normalized vectors)",
        "ready_for_embedding": True,
    }


def save_vectorstore_report(report: dict, output_path: Path) -> None:
    """
    Save vector store report as JSON.
    
    Args:
        report: Vector store metrics dict
        output_path: Path where report will be saved
        
    Note:
        Called by: main() to provide overview for user validation
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Vector store report saved to {output_path}")


def log_report_summary(report: dict) -> None:
    """
    Log key metrics from report to console.
    
    Args:
        report: Vector store metrics dict
        
    Note:
        Called by: main() to show summary without reading JSON
        Pure logging function with no return value
    """
    logger.info(f"\nTotal chunks in vector store: {report['total_chunks']}")
    logger.info(f"Books indexed: {report['unique_books']}")
    logger.info(f"Chapters indexed: {report['unique_chapters']}")
    logger.info(f"Sections indexed: {report['unique_sections']}")
    logger.info(f"Average text length: {report['avg_text_length']:.0f} characters")
    logger.info(f"Index type: {report['index_type']}")
    logger.info(f"Similarity metric: {report['similarity_metric']}")


def main() -> None:
    """
    Main orchestration function for Stage 3.
    
    Coordinates:
    1. Ensuring output directories exist
    2. Loading all augmented chunks with schema validation
    3. Creating FAISS index structure (IndexFlatIP for cosine similarity)
    4. Saving structure and metadata (as JSON not pickle)
    5. Generating validation report
    
    Note:
        User should verify structure before proceeding to stage_4_generate_embeddings.py
        Schema validation prevents mismatches from causing runtime failures
    """
    logger.info("=" * 80)
    logger.info("STAGE 3: VECTOR STORE CREATION")
    logger.info("=" * 80)

    PathConfig.ensure_directories()

    try:
        metadata = prepare_vectorstore_data()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to prepare metadata: {e}")
        return

    if not metadata:
        logger.error("No metadata prepared. Check Stage 2 output.")
        return

    index = create_empty_faiss_index(VectorStoreConfig.EMBEDDING_DIMENSION)

    save_vectorstore_structure(index, metadata, PathConfig.STAGE_3_OUTPUT_DIR)

    report = generate_vectorstore_report(metadata)
    report_path = PathConfig.STAGE_3_OUTPUT_DIR / "vectorstore_report.json"
    save_vectorstore_report(report, report_path)

    logger.info("\n" + "=" * 80)
    logger.info("STAGE 3 COMPLETE")
    logger.info("=" * 80)
    
    log_report_summary(report)
    
    logger.info(f"\nOutput directory: {PathConfig.STAGE_3_OUTPUT_DIR}")
    logger.info("\nNext steps:")
    logger.info("1. Review vectorstore_report.json")
    logger.info("2. Verify chunk counts match Stage 2 output")
    logger.info("3. Check that schema validation passed")
    logger.info("4. If satisfied, run stage_4_generate_embeddings.py")
    logger.info("\nNote: Stage 4 will generate and normalize embeddings for cosine similarity")


if __name__ == "__main__":
    main()