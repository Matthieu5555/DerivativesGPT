from pathlib import Path
from google.cloud import storage
from typing import List
import os
from dotenv import load_dotenv

# Load .env from project root (two levels up from this script)
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configuration - reads from .env
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
REGION = os.getenv("GCP_REGION")
LOCAL_PDF_DIR = Path(os.getenv("LOCAL_PDF_DIR"))
BUCKET_NAME = f"{PROJECT_ID}-nougat-ocr"

def create_bucket(project_id: str, bucket_name: str, region: str) -> storage.Bucket:
    """
    Creates a GCS bucket in the specified region.
    This bucket will store input PDFs and output results.
    Called by: main function for initial setup.
    """
    client = storage.Client(project=project_id)
    
    try:
        bucket = client.get_bucket(bucket_name)
        print(f"✓ Bucket already exists: gs://{bucket_name}")
        return bucket
    except Exception:
        bucket = client.create_bucket(
            bucket_name,
            location=region
        )
        print(f"✓ Created bucket: gs://{bucket_name}")
        return bucket

def upload_pdfs(bucket: storage.Bucket, local_dir: Path) -> List[str]:
    """
    Uploads all PDF files from local directory to GCS bucket input folder.
    This function prepares files for processing by the Nougat pipeline.
    Called by: main function after bucket creation.
    Returns: List of uploaded file paths in GCS.
    """
    pdf_files = sorted(local_dir.glob("*.pdf"))
    
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {local_dir}")
    
    uploaded_files = []
    
    for pdf_path in pdf_files:
        blob_name = f"input/{pdf_path.name}"
        blob = bucket.blob(blob_name)
        
        blob.upload_from_filename(str(pdf_path))
        gcs_path = f"gs://{bucket.name}/{blob_name}"
        uploaded_files.append(gcs_path)
        
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        print(f"✓ Uploaded {pdf_path.name} ({size_mb:.2f} MB) → {gcs_path}")
    
    return uploaded_files

def main() -> None:
    """
    Orchestrates bucket creation and PDF upload process.
    This is the entry point for setting up GCS storage for the Nougat pipeline.
    """
    print(f"Configuration:")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Region: {REGION}")
    print(f"  Bucket: {BUCKET_NAME}")
    print(f"  PDF Directory: {LOCAL_PDF_DIR}\n")
    
    bucket = create_bucket(PROJECT_ID, BUCKET_NAME, REGION)
    uploaded_files = upload_pdfs(bucket, LOCAL_PDF_DIR)
    
    print(f"\n=== Upload Complete ===")
    print(f"Total files: {len(uploaded_files)}")
    print(f"Bucket: gs://{BUCKET_NAME}")

if __name__ == "__main__":
    main()