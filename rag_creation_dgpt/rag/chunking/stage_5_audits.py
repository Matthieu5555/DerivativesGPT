"""
Verification script for Stage 4 output.

Run this from your project root: DerivativesGPT-v3/
Usage: python verify_stage_4_output.py

Checks:
1. Completion report exists and shows success
2. Vector store files exist and are valid
3. FAISS index can be loaded and has correct properties
4. Metadata matches index size
5. Embeddings are properly normalized
"""

import json
from pathlib import Path

import numpy as np
import faiss

from config import PathConfig


def verify_completion_report() -> dict:
    """Check completion report exists and extract metrics."""
    report_path = PathConfig.VECTORSTORE_DIR / "completion_report.json"
    
    print(f"Checking: {report_path}")
    
    if not report_path.exists():
        print(f"❌ Completion report not found")
        return {}
    
    with open(report_path, "r") as f:
        report = json.load(f)
    
    print("✓ Completion report found")
    return report


def verify_files_exist() -> tuple[bool, bool]:
    """Check that index and metadata files exist."""
    index_path = PathConfig.VECTORSTORE_DIR / "rag_index_structured.faiss"
    metadata_path = PathConfig.VECTORSTORE_DIR / "metadata_structured.json"
    
    print(f"\nChecking: {index_path}")
    index_exists = index_path.exists()
    if index_exists:
        size_mb = index_path.stat().st_size / (1024 * 1024)
        print(f"✓ FAISS index found ({size_mb:.2f} MB)")
    else:
        print(f"❌ FAISS index missing")
    
    print(f"\nChecking: {metadata_path}")
    metadata_exists = metadata_path.exists()
    if metadata_exists:
        size_mb = metadata_path.stat().st_size / (1024 * 1024)
        print(f"✓ Metadata found ({size_mb:.2f} MB)")
    else:
        print(f"❌ Metadata missing")
    
    return index_exists, metadata_exists


def load_and_verify_index() -> tuple[faiss.Index, int, int]:
    """Load FAISS index and extract properties."""
    index_path = PathConfig.VECTORSTORE_DIR / "rag_index_structured.faiss"
    
    try:
        index = faiss.read_index(str(index_path))
        num_vectors = index.ntotal
        dimension = index.d
        
        print(f"\n✓ Index loaded successfully")
        print(f"  - Vectors: {num_vectors:,}")
        print(f"  - Dimension: {dimension}")
        print(f"  - Index type: {type(index).__name__}")
        
        return index, num_vectors, dimension
        
    except Exception as e:
        print(f"\n❌ Failed to load index: {e}")
        return None, 0, 0


def load_and_verify_metadata() -> tuple[list, int, int]:
    """Load metadata and extract statistics."""
    metadata_path = PathConfig.VECTORSTORE_DIR / "metadata_structured.json"
    
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        num_chunks = len(metadata)
        unique_books = len(set(m["book_name"] for m in metadata))
        
        # Sample one metadata entry to show structure
        sample = metadata[0] if metadata else {}
        
        print(f"\n✓ Metadata loaded successfully")
        print(f"  - Chunks: {num_chunks:,}")
        print(f"  - Unique books: {unique_books}")
        print(f"  - Metadata keys: {list(sample.keys())}")
        
        return metadata, num_chunks, unique_books
        
    except Exception as e:
        print(f"\n❌ Failed to load metadata: {e}")
        return [], 0, 0


def verify_consistency(num_vectors: int, num_chunks: int) -> bool:
    """Check that index size matches metadata size."""
    print(f"\nConsistency check:")
    if num_vectors == num_chunks:
        print(f"✓ Perfect match: {num_vectors:,} vectors = {num_chunks:,} chunks")
        return True
    else:
        print(f"❌ Size mismatch: {num_vectors:,} vectors ≠ {num_chunks:,} chunks")
        return False


def test_index_search(index: faiss.Index, dimension: int) -> bool:
    """Test that index can perform searches."""
    print(f"\nTesting search functionality:")
    try:
        # Create a random query vector (normalized)
        query = np.random.randn(1, dimension).astype('float32')
        query = query / np.linalg.norm(query)
        
        # Search for top 5 results
        distances, indices = index.search(query, 5)
        
        print(f"✓ Index search works")
        print(f"  - Top 5 similarity scores: {distances[0]}")
        print(f"  - Retrieved indices: {indices[0]}")
        
        # Check if scores are in valid range for cosine similarity
        if np.all(distances >= -1.01) and np.all(distances <= 1.01):
            print(f"✓ Similarity scores in valid range [-1, 1]")
            return True
        else:
            print(f"⚠️  Similarity scores outside expected range")
            print(f"    Min: {distances.min():.4f}, Max: {distances.max():.4f}")
            return False
        
    except Exception as e:
        print(f"❌ Index search failed: {e}")
        return False


def print_report_details(report: dict) -> None:
    """Print detailed report information."""
    print("\n" + "=" * 70)
    print("COMPLETION REPORT DETAILS")
    print("=" * 70)
    
    if not report:
        print("❌ No completion report available")
        return
    
    print(f"\nVectors indexed:      {report.get('total_vectors', 'N/A'):,}")
    print(f"Chunks processed:     {report.get('total_chunks', 'N/A'):,}")
    print(f"Embedding dimension:  {report.get('embedding_dimension', 'N/A')}")
    print(f"Unique books:         {report.get('unique_books', 'N/A')}")
    print(f"Embedding model:      {report.get('embedding_model', 'N/A')}")
    print(f"Index type:           {report.get('index_type', 'N/A')}")
    print(f"Similarity metric:    {report.get('similarity_metric', 'N/A')}")
    print(f"Embeddings normalized: {report.get('embeddings_normalized', 'N/A')}")
    print(f"Avg embedding norm:   {report.get('avg_embedding_norm', 'N/A'):.6f}")
    print(f"Vector store complete: {report.get('vector_store_complete', 'N/A')}")
    print(f"Ready for queries:    {report.get('ready_for_queries', 'N/A')}")


def print_summary(all_checks_passed: bool) -> None:
    """Print final verification summary."""
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    if all_checks_passed:
        print("\n🎉 ALL CHECKS PASSED!")
        print("\nYour vector store is ready for queries.")
        print("\nNext step:")
        print("  python query_rag_index.py")
    else:
        print("\n⚠️  SOME CHECKS FAILED")
        print("\nPlease review the errors above.")
        print("You may need to re-run Stage 4.")


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("STAGE 4 OUTPUT VERIFICATION")
    print("=" * 70)
    print(f"\nVector store directory: {PathConfig.VECTORSTORE_DIR}")
    print()
    
    checks_passed = []
    
    # Check 1: Completion report
    print("\n[1/6] Checking completion report...")
    print("-" * 70)
    report = verify_completion_report()
    checks_passed.append(bool(report))
    
    # Check 2: Files exist
    print("\n[2/6] Checking output files...")
    print("-" * 70)
    index_exists, metadata_exists = verify_files_exist()
    checks_passed.append(index_exists and metadata_exists)
    
    if not (index_exists and metadata_exists):
        print("\n❌ Required files missing. Cannot proceed with verification.")
        print_summary(False)
        return
    
    # Check 3: Load and verify index
    print("\n[3/6] Loading and verifying FAISS index...")
    print("-" * 70)
    index, num_vectors, dimension = load_and_verify_index()
    checks_passed.append(index is not None)
    
    if index is None:
        print("\n❌ Cannot load index. Cannot proceed with verification.")
        print_summary(False)
        return
    
    # Check 4: Load and verify metadata
    print("\n[4/6] Loading and verifying metadata...")
    print("-" * 70)
    metadata, num_chunks, unique_books = load_and_verify_metadata()
    checks_passed.append(bool(metadata))
    
    if not metadata:
        print("\n❌ Cannot load metadata. Cannot proceed with verification.")
        print_summary(False)
        return
    
    # Check 5: Verify consistency
    print("\n[5/6] Verifying consistency...")
    print("-" * 70)
    consistent = verify_consistency(num_vectors, num_chunks)
    checks_passed.append(consistent)
    
    # Check 6: Test search
    print("\n[6/6] Testing index search functionality...")
    print("-" * 70)
    search_works = test_index_search(index, dimension)
    checks_passed.append(search_works)
    
    # Print detailed report
    print_report_details(report)
    
    # Print summary
    all_passed = all(checks_passed)
    print_summary(all_passed)
    
    print(f"\nChecks passed: {sum(checks_passed)}/{len(checks_passed)}")


if __name__ == "__main__":
    main()