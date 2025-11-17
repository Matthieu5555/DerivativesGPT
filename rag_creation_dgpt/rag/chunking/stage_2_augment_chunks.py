"""
Stage 2: Chunk Augmentation with Summaries

This script augments chunks from Stage 1 by:
1. Loading chunks from Stage 1 output (*_chunks.json)
2. Generating chapter-level summaries using a configurable LLM provider
   (OpenRouter or Google Gemini)
3. Adding summaries to chunk metadata
4. Saving augmented chunks for validation
"""

import json
import logging
import time
import os
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

# --- Core LangChain Imports ---
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.schema import HumanMessage
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# --- Provider-Specific Imports ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from google.api_core.exceptions import (
    PermissionDenied, 
    Unauthenticated, 
    NotFound, 
    GoogleAPICallError
)

# --- Config Import ---
# This adds the 'rag' directory to the path to find 'config'
sys.path.append(str(Path(__file__).parent.parent))
try:
    from config import PathConfig, AugmentationConfig
except ImportError:
    logging.basicConfig(level=logging.ERROR)
    logger_cfg = logging.getLogger(__name__)
    logger_cfg.error("Failed to import config.py.")
    logger_cfg.error("Ensure config.py is in the 'rag' directory, one level above 'chunking'.")
    sys.exit(1)
# --- End of imports ---


# --- Configuration Constants ---
# Load environment variables
load_dotenv()

# General LLM settings
LLM_TEMPERATURE: float = 0.3
LLM_MAX_OUTPUT_TOKENS: int = 2048

# Provider switch
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")  # Default to google if not set

# Google-specific settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# OpenRouter-specific settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- START OF FIX ---
# 'google/gemini-1.5-pro-latest' was invalid.
# The correct OpenRouter ID is 'google/gemini-1.5-pro'
OPENROUTER_MODEL = "google/gemini-2.5-flash"
# --- END OF FIX ---
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class AugmentedChunk:
    """Chunk with added chapter summary."""
    chunk_id: str
    book_name: str
    chapter_number: Optional[int]
    chapter_title: str
    chunk_index_in_chapter: int
    total_chunks_in_chapter: int
    text: str
    char_start: int
    char_end: int
    chunking_method: str
    confidence: float
    position_percent: float
    chapter_summary: str


# --- Provider-Agnostic LLM Initialization ---

def _init_openrouter_client() -> BaseChatModel:
    """Initializes and validates the OpenRouter client."""
    if not OPENROUTER_API_KEY:
        raise ValueError("LLM_PROVIDER is 'openrouter' but OPENROUTER_API_KEY is not set.")
    
    logger.info(f"Initializing OpenRouter with model: {OPENROUTER_MODEL}")
    try:
        # Use ChatOpenAI and point it to OpenRouter's base URL
        model = ChatOpenAI(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_OUTPUT_TOKENS,
        )

        # Eagerly validate credentials and model name
        model.invoke("test", config={"max_output_tokens": 1})
        logger.info(f"Successfully initialized and validated OpenRouter model: {OPENROUTER_MODEL}")
        return model
    except Exception as e:
        logger.error(f"Failed to initialize OpenRouter: {e}")
        raise

def _init_google_client() -> BaseChatModel:
    """Initializes and validates the Google Gemini client."""
    if not GEMINI_API_KEY:
        raise ValueError("LLM_PROVIDER is 'google' but GEMINI_API_KEY is not set.")

    logger.info("Initializing Google Gemini client...")
    models_to_try = [
        "gemini-1.5-pro", 
        "gemini-1.5-flash",
        "gemini-pro",
    ]
    
    last_error = None
    
    for model_name in models_to_try:
        try:
            model = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=GEMINI_API_KEY,
                temperature=LLM_TEMPERATURE,
                max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
                api_version="v1", # Fixes the v1beta 404 error
            )
            # Eagerly validate credentials and model name
            model.invoke("test", config={"max_output_tokens": 1})
            logger.info(f"Successfully initialized and validated Google model: {model_name}")
            return model
            
        except (PermissionDenied, Unauthenticated) as e:
            logger.error(f"Google API key or permission error: {e}")
            raise ValueError(f"Google API key or permission error: {e}")
        except (NotFound, GoogleAPICallError, Exception) as e:
            logger.warning(f"Google model '{model_name}' failed. Trying next. Error: {e}")
            last_error = e
            continue
            
    logger.error(f"No working Google model found. Tried: {models_to_try}")
    if last_error:
        raise ValueError(f"All Google models failed. Last error: {last_error}")
    raise ValueError("No Google models found or all failed to initialize.")


def init_llm_client() -> BaseChatModel:
    """
    Factory function to initialize the correct LLM client based on
    the LLM_PROVIDER environment variable.
    """
    if LLM_PROVIDER == "openrouter":
        return _init_openrouter_client()
    elif LLM_PROVIDER == "google":
        return _init_google_client()
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: '{LLM_PROVIDER}'. Must be 'openrouter' or 'google'.")


# --- Core Logic (Unchanged, but types updated) ---

@retry(
    stop=stop_after_attempt(AugmentationConfig.MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def summarize_chapter(model: BaseChatModel, chapter_text: str, chapter_name: str) -> str:
    """Generate concise chapter summary using the provided LangChain model."""
    try:
        # Prompt logic remains the same
        if any(keyword in chapter_name.lower() for keyword in ["gap", "between", "pre-ch", "post-ch", "likely"]):
            prompt = f"""Provide a 2-3 sentence summary of this content that appears to be from missing or undetected chapters in an academic textbook.
Focus on the main concepts or methods discussed, acknowledging this may be transitional content.

Section: {chapter_name}

Text:
{chapter_text}"""
        else:
            prompt = f"""Provide a clear, informative 2-3 sentence summary of this chapter from an academic textbook.
Focus on the main concepts, methods, or findings discussed.

Chapter: {chapter_name}

Text:
{chapter_text}"""

        message = HumanMessage(content=prompt)
        # model.invoke() is the standard interface for all BaseChatModel subclasses
        response = model.invoke([message])
        time.sleep(AugmentationConfig.API_CALL_DELAY)

        return response.content.strip() if response.content else "Summary unavailable."

    except Exception as e:
        logger.warning(f"Summarization failed for {chapter_name}: {e}")
        return "Summary unavailable."


def load_chunks_from_stage1(filepath: Path) -> List[Dict[str, Any]]:
    """Load chunks from Stage 1 JSON output."""
    with open(filepath, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    logger.info(f"Loaded {len(chunks)} chunks from {filepath.name}")
    return chunks


def prepare_chapter_text(chunks: List[Dict[str, Any]], chapter_title: str) -> str:
    """Combine all chunk texts for a chapter into single string."""
    chapter_chunks = [c for c in chunks if c["chapter_title"] == chapter_title]
    combined_text = "\n\n".join(c["text"] for c in chapter_chunks)

    return combined_text[:AugmentationConfig.MAX_INPUT_LENGTH]


def augment_book_chunks(input_path: Path, model: BaseChatModel) -> List[AugmentedChunk]:
    """Add chapter summaries to all chunks from one book."""
    chunks = load_chunks_from_stage1(input_path)

    unique_chapters = list(dict.fromkeys(c["chapter_title"] for c in chunks))
    logger.info(f"Processing {len(unique_chapters)} unique chapters/sections")

    chapter_summaries: Dict[str, str] = {}

    for chapter_title in unique_chapters:
        logger.info(f"Summarizing: {chapter_title}")

        chapter_text = prepare_chapter_text(chunks, chapter_title)
        
        if len(chapter_text.strip()) < 100:
            chapter_summaries[chapter_title] = "Section too short for summary."
        else:
            summary = summarize_chapter(model, chapter_text, chapter_title)
            chapter_summaries[chapter_title] = summary

    augmented_chunks: List[AugmentedChunk] = []

    for chunk in chunks:
        augmented = AugmentedChunk(
            chunk_id=chunk["chunk_id"],
            book_name=chunk["book_name"],
            chapter_number=chunk.get("chapter_number"),
            chapter_title=chunk["chapter_title"],
            chunk_index_in_chapter=chunk["chunk_index_in_chapter"],
            total_chunks_in_chapter=chunk["total_chunks_in_chapter"],
            text=chunk["text"],
            char_start=chunk["char_start"],
            char_end=chunk["char_end"],
            chunking_method=chunk["chunking_method"],
            confidence=chunk["confidence"],
            position_percent=chunk["position_percent"],
            chapter_summary=chapter_summaries[chunk["chapter_title"]],
        )
        augmented_chunks.append(augmented)

    logger.info(f"Augmented {len(augmented_chunks)} chunks")
    return augmented_chunks


def save_augmented_chunks(chunks: List[AugmentedChunk], output_path: Path) -> None:
    """Save augmented chunks to JSON file for validation."""
    chunk_dicts = [asdict(chunk) for chunk in chunks]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunk_dicts, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(chunks)} augmented chunks to {output_path}")


def generate_augmentation_report(all_chunks: List[AugmentedChunk]) -> Dict[str, Any]:
    """Create summary statistics for augmentation validation."""
    if not all_chunks:
        return {}

    summaries_generated = sum(
        1 for c in all_chunks 
        if c.chapter_summary not in ["Summary unavailable.", "Section too short for summary."]
    )

    unique_summaries = len(
        set(c.chapter_summary for c in all_chunks 
            if c.chapter_summary not in ["Summary unavailable.", "Section too short for summary."])
    )

    summary_lengths = [
        len(c.chapter_summary) for c in all_chunks 
        if c.chapter_summary not in ["Summary unavailable.", "Section too short for summary."]
    ]

    avg_summary_length = sum(summary_lengths) / len(summary_lengths) if summary_lengths else 0

    detected_chunks = sum(1 for c in all_chunks if c.chapter_number is not None)
    gap_chunks = sum(1 for c in all_chunks if c.chapter_number is None)

    return {
        "total_chunks": len(all_chunks),
        "detected_chapter_chunks": detected_chunks,
        "gap_chunks": gap_chunks,
        "summaries_generated": summaries_generated,
        "unique_summaries": unique_summaries,
        "avg_summary_length": avg_summary_length,
        "success_rate": (summaries_generated / len(all_chunks) * 100) if all_chunks else 0,
    }


def save_augmentation_report(report: Dict[str, Any], output_path: Path) -> None:
    """Save augmentation report as JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Augmentation report saved to {output_path}")


def process_all_books(model: BaseChatModel) -> List[AugmentedChunk]:
    """Augment chunks from all books in Stage 1 output."""
    input_files = sorted(PathConfig.STAGE_1_OUTPUT_DIR.glob("*_chunks.json"))
    
    excluded_patterns = ['_boundaries.json', 'detection_stats.json', 
                         'validation_report.json', 'stage1_stats.json']
    input_files = [
        f for f in input_files 
        if not any(pattern in f.name for pattern in excluded_patterns)
    ]

    if not input_files:
        logger.error(f"No Stage 1 chunk files found in {PathConfig.STAGE_1_OUTPUT_DIR}")
        logger.error("Please run stage_1_basic_chunking.py first")
        return []

    logger.info(f"Found {len(input_files)} files to augment")

    all_augmented: List[AugmentedChunk] = []

    for input_file in input_files:
        logger.info(f"\nProcessing {input_file.name}")

        try:
            augmented_chunks = augment_book_chunks(input_file, model)

            if augmented_chunks:
                output_filename = input_file.name.replace("_chunks.json", "_augmented.json")
                output_path = PathConfig.STAGE_2_OUTPUT_DIR / output_filename
                save_augmented_chunks(augmented_chunks, output_path)
                all_augmented.extend(augmented_chunks)
        
        except Exception as e:
            logger.error(f"Failed to process {input_file.name}: {e}")
            continue

    return all_augmented


def main() -> None:
    """Main orchestration function for Stage 2."""
    logger.info("="*80)
    logger.info("STAGE 2: CHUNK AUGMENTATION WITH SUMMARIES")
    logger.info(f"Using LLM Provider: {LLM_PROVIDER}")
    logger.info("="*80)

    PathConfig.ensure_directories()

    try:
        # The main call is now to the new, flexible function
        model = init_llm_client()
    except (ValueError, ImportError) as e:
        logger.error(f"Failed to initialize model: {e}")
        logger.error("Exiting Stage 2.")
        return

    all_augmented = process_all_books(model)

    if not all_augmented:
        logger.error("No chunks augmented. Check Stage 1 output and API credentials.")
        return

    report = generate_augmentation_report(all_augmented)
    report_path = PathConfig.STAGE_2_OUTPUT_DIR / "augmentation_report.json"
    save_augmentation_report(report, report_path)

    logger.info("\n" + "="*80)
    logger.info("STAGE 2 COMPLETE")
    logger.info("="*80)
    logger.info(f"\nTotal chunks augmented: {report['total_chunks']}")
    logger.info(f"Detected chapter chunks: {report['detected_chapter_chunks']}")
    logger.info(f"Gap chunks: {report['gap_chunks']}")
    logger.info(f"Summaries generated: {report['summaries_generated']}")
    logger.info(f"Unique summaries: {report['unique_summaries']}")
    logger.info(f"Success rate: {report['success_rate']:.1f}%")
    logger.info(f"Average summary length: {report['avg_summary_length']:.0f} characters")
    logger.info(f"\nOutput directory: {PathConfig.STAGE_2_OUTPUT_DIR}")
    logger.info("\nNext steps:")
    logger.info("1. Review augmented chunks in output directory")
    logger.info("2. Inspect augmentation_report.json")
    logger.info("3. Verify summary quality for sample chapters")
    logger.info("4. If satisfied, run stage_3_create_vectorstore.py")


if __name__ == "__main__":
    main()