"""
Centralized Configuration for RAG Chunking Pipeline

This configuration module centralizes all paths, API settings, and parameters
for the 4-stage chunking pipeline. All variables are loaded from environment
variables with sensible defaults.

Used by: All stage scripts (1-4) and query_rag_index.py
"""

import os
from pathlib import Path
from typing import Final


class PathConfig:
    """
    Path configuration for pipeline input/output locations.
    
    All paths are OS-independent using pathlib.
    Called by: All pipeline stages for file I/O operations
    """
    
    # Project root directory - always resolves to DerivativesGPT-v3/
    # This file is at: DerivativesGPT-v3/rag/chunking/config.py
    # So we go up 2 levels: config.py -> chunking -> rag -> DerivativesGPT-v3
    PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent
    
    # Base data directory - root for all pipeline data
    # Used by: All stages to locate inputs and create outputs
    BASE_DIR: Final[Path] = PROJECT_ROOT / "data"
    
    # Document input directory - where source .mmd files are located
    # Used by: stage_1_basic_chunking.py to find documents
    DOCUMENTS_DIR: Final[Path] = PROJECT_ROOT / "rag" / "chunking" / "documents"
    
    # Manual chapter definitions for books where auto-detection fails
    # Used by: chapter_detection.py as fallback when automatic detection is insufficient
    MANUAL_CHAPTERS_YAML: Final[Path] = PROJECT_ROOT / "rag" / "chunking" / "documents" / "manual_chapters.yaml"
    
    # Intermediate chunking stages directory
    # Used by: All stages to read/write intermediate results
    CHUNKING_STAGES_DIR: Final[Path] = BASE_DIR / "chunking_stages"
    
    # Stage 1 output - basic chunks without augmentation
    # Used by: stage_1 to write, stage_2 to read
    STAGE_1_OUTPUT_DIR: Final[Path] = CHUNKING_STAGES_DIR / "stage_1_basic_chunks"
    
    # Stage 2 output - chunks with chapter summaries
    # Used by: stage_2 to write, stage_3 to read
    STAGE_2_OUTPUT_DIR: Final[Path] = CHUNKING_STAGES_DIR / "stage_2_augmented_chunks"
    
    # Stage 3 output - vector store structure (no embeddings yet)
    # Used by: stage_3 to write, stage_4 to read
    STAGE_3_OUTPUT_DIR: Final[Path] = CHUNKING_STAGES_DIR / "stage_3_vectorstore"
    
    # Final vector store with embeddings
    # Used by: stage_4 to write, query_rag_index.py to read
    VECTORSTORE_DIR: Final[Path] = BASE_DIR / "vectorstore"
    
    @classmethod
    def ensure_directories(cls) -> None:
        """
        Create all output directories if they don't exist.
        
        Called by: Each stage's main() before processing
        Ensures: All output directories exist before writing
        """
        cls.STAGE_1_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.STAGE_2_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.STAGE_3_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)


class GeminiConfig:
    """
    Gemini API configuration for summarization and embeddings.
    
    All settings use Gemini API (no Vertex AI required).
    Called by: stage_2 (summaries), stage_4 (embeddings), query script
    """
    
    # Gemini API key for authentication
    # Used by: All Gemini API calls via genai.configure()
    API_KEY: Final[str] = os.getenv("GEMINI_API_KEY", "")
    
    # Model for text generation (summaries, answers)
    # Used by: stage_2_augment_chunks.py, query_rag_index.py
    GENERATION_MODEL: Final[str] = "gemini-2.5-flash"
    
    # Model for text embeddings
    # Used by: stage_4_generate_embeddings.py, query_rag_index.py
    # text-embedding-004 outputs 768 dimensions
    EMBEDDING_MODEL: Final[str] = "models/text-embedding-004"
    
    # Task type for document embeddings during indexing
    # Used by: stage_4 when creating embeddings for storage
    EMBEDDING_TASK_TYPE_DOCUMENT: Final[str] = "RETRIEVAL_DOCUMENT"
    
    # Task type for query embeddings during search
    # Used by: query_rag_index.py when embedding search queries
    EMBEDDING_TASK_TYPE_QUERY: Final[str] = "RETRIEVAL_QUERY"
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required API credentials are configured.
        
        Returns:
            True if API key is set, False otherwise
            
        Called by: stage_2 and stage_4 main() before API operations
        """
        if not cls.API_KEY:
            return False
        return True


class ChunkingConfig:
    """
    Parameters for text chunking behavior.
    
    Controls how documents are split into processable chunks.
    Called by: stage_1_basic_chunking.py
    """
    
    # Maximum chunk size in characters
    # Used by: chunk_section() to determine when to split text
    MAX_CHUNK_SIZE: Final[int] = 1000
    MIN_CHUNK_SIZE: Final[int] = 100
    
    # Overlap between consecutive chunks in characters
    # Used by: chunk_section() to preserve context at boundaries
    CHUNK_OVERLAP: Final[int] = 100
    
    # Patterns to detect chapter starts in markdown
    # Used by: detect_first_chapter() to identify book content start
    CHAPTER_START_PATTERNS: Final[list[str]] = [
        r"^#+\s*Chapter\s+(\d+|[IVX]+)",
        r"^#+\s*(\d+)\.\s+[A-Z]",
        r"^CHAPTER\s+(\d+|[IVX]+)",
    ]
    
    # Keywords identifying front matter to skip
    # Used by: detect_first_chapter() to skip non-content pages
    FRONT_MATTER_KEYWORDS: Final[list[str]] = [
        "copyright",
        "preface",
        "foreword",
        "dedication",
        "acknowledgment",
        "table of contents",
        "contents",
        "praise for",
        "about the author",
    ]


class AugmentationConfig:
    """
    Parameters for chunk augmentation with summaries.
    
    Controls API behavior during summary generation.
    Called by: stage_2_augment_chunks.py
    """
    
    # Delay between API calls in seconds
    # Used by: summarize_chapter() to respect rate limits
    API_CALL_DELAY: Final[float] = 1.0
    
    # Maximum retries for failed API calls
    # Used by: @retry decorator on summarize_chapter()
    MAX_RETRIES: Final[int] = 3
    
    # Maximum input length for summarization (characters)
    # Used by: prepare_chapter_text() to avoid token limit errors
    MAX_INPUT_LENGTH: Final[int] = 5000


class VectorStoreConfig:
    """
    Configuration for FAISS vector store.
    
    Defines embedding dimensions and index structure.
    Called by: stage_3_create_vectorstore.py, stage_4_generate_embeddings.py
    """
    
    # Embedding vector dimension
    # Used by: create_empty_faiss_index() to initialize index structure
    # Must match EMBEDDING_MODEL output: text-embedding-004 = 768
    EMBEDDING_DIMENSION: Final[int] = 768
    
    # Batch size for embedding generation
    # Used by: generate_embeddings() to group API calls
    EMBEDDING_BATCH_SIZE: Final[int] = 10
    
    # Delay between embedding batches in seconds
    # Used by: generate_embeddings() to avoid rate limit errors
    BATCH_DELAY: Final[float] = 0.5


class QueryConfig:
    """
    Configuration for RAG query interface.
    
    Controls search behavior and result formatting.
    Called by: query_rag_index.py
    """
    
    # Number of top results to return per query
    # Used by: search_index() to limit result set
    TOP_K: Final[int] = 5


def validate_all_configs() -> tuple[bool, list[str]]:
    """
    Validate all configuration settings.
    
    Returns:
        Tuple of (is_valid, error_messages)
        
    Called by: Pipeline scripts before starting processing
    Ensures: All required settings are properly configured
    """
    errors = []
    
    if not GeminiConfig.validate():
        errors.append("GEMINI_API_KEY environment variable not set")
    
    if not PathConfig.DOCUMENTS_DIR.exists():
        errors.append(f"Documents directory not found: {PathConfig.DOCUMENTS_DIR}")
    
    if VectorStoreConfig.EMBEDDING_DIMENSION != 768 and GeminiConfig.EMBEDDING_MODEL == "models/text-embedding-004":
        errors.append("EMBEDDING_DIMENSION (768) doesn't match text-embedding-004 output")
    
    is_valid = len(errors) == 0
    return is_valid, errors