#!/usr/bin/env python3
"""
Nougat OCR Pipeline - Production Ready Version
Processes PDFs with adaptive batch sizing, memory management, and GCS integration
"""

import os
import gc
import json
import time
import signal
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import torch
import pypdfium2 as pdfium
from google.cloud import storage
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration constants
MAX_RETRIES = 3  # Retry attempts for GCS operations
PROCESSING_TIMEOUT = 14400  # 4 hours per PDF
WORK_DIR = Path("/app/work")  # Using 100GB disk space
OUTPUT_DIR = Path("/app/outputs")

# Memory management settings
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Force unbuffered output for Vertex AI
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


class PDFRiskLevel:
    """Enum for PDF processing risk levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


class NougatProcessor:
    """Main processor class for Nougat OCR pipeline"""
    
    def __init__(self):
        """Initialize processor with configuration from environment"""
        self.bucket_name = os.environ.get("BUCKET_NAME", "llm-ops-475209-nougat-ocr")
        self.input_prefix = os.environ.get("INPUT_PREFIX", "input/").rstrip('/') + '/'
        self.output_prefix = os.environ.get("OUTPUT_PREFIX", "output/").rstrip('/') + '/'
        
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        # Create working directories
        WORK_DIR.mkdir(exist_ok=True, parents=True)
        OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
        
        # Processing statistics
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "timeout": 0,
            "blocked": 0,
            "oom_errors": 0
        }
        
        logger.info(f"Initialized NougatProcessor")
        logger.info(f"Bucket: {self.bucket_name}")
        logger.info(f"Input: {self.input_prefix}")
        logger.info(f"Output: {self.output_prefix}")
    
    def run(self) -> None:
        """Main pipeline execution"""
        start_time = time.time()
        
        try:
            # Pre-flight checks
            self._preflight_checks()
            
            # Download PDFs
            pdf_files = self._download_pdfs()
            if not pdf_files:
                logger.warning("No PDFs found to process")
                return
            
            logger.info(f"Found {len(pdf_files)} PDFs to process")
            results = []
            
            # Process each PDF sequentially
            for idx, pdf_path in enumerate(pdf_files, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"[{idx}/{len(pdf_files)}] Processing: {pdf_path.name}")
                logger.info(f"{'='*60}")
                
                # Clean memory before each PDF
                self._cleanup_gpu_memory()
                
                # Assess PDF risk
                risk_level = self._assess_pdf_risk(pdf_path)
                
                if risk_level == PDFRiskLevel.BLOCKED:
                    logger.warning(f"Skipping blocked PDF (encrypted/corrupted)")
                    results.append({
                        "pdf": pdf_path.name,
                        "status": "blocked",
                        "reason": "encrypted_or_corrupted"
                    })
                    self.stats["blocked"] += 1
                    continue
                
                # Process with adaptive batch size
                result = self._process_pdf_adaptive(pdf_path, risk_level)
                results.append(result)
                
                # Update statistics
                self._update_stats(result)
                
                # Clean up PDF file to free space
                if pdf_path.exists():
                    pdf_path.unlink()
            
            # Create and upload manifest
            manifest = self._create_manifest(results, start_time)
            self._upload_manifest(manifest)
            
            # Final report
            self._report_final_status(manifest)
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
    
    def _preflight_checks(self) -> None:
        """Validate environment before starting"""
        logger.info("Running preflight checks...")
        
        # Check GPU
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"✓ GPU: {gpu_name} ({gpu_mem:.1f}GB)")
            
            if gpu_mem < 14:
                raise RuntimeError(f"Insufficient GPU memory: {gpu_mem:.1f}GB (need >=14GB)")
        else:
            logger.warning("⚠ No GPU available - processing will be slow")
        
        # Test GCS access
        try:
            list(self.bucket.list_blobs(prefix=self.input_prefix, max_results=1))
            logger.info(f"✓ GCS access confirmed")
        except Exception as e:
            raise RuntimeError(f"Cannot access GCS bucket: {e}")
        
        # Check disk space
        disk_free = os.statvfs('/app').f_bavail * os.statvfs('/app').f_frsize / 1e9
        logger.info(f"✓ Disk space: {disk_free:.1f}GB free")
        
        if disk_free < 10:
            raise RuntimeError(f"Insufficient disk space: {disk_free:.1f}GB (need >=10GB)")
    
    def _cleanup_gpu_memory(self) -> None:
        """Force complete GPU memory cleanup"""
        if torch.cuda.is_available():
            # Clear PyTorch cache
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            # Force garbage collection multiple times
            for _ in range(3):
                gc.collect()
            
            # Final cleanup
            torch.cuda.empty_cache()
            
            # Log current memory status
            free_memory = torch.cuda.mem_get_info()[0] / 1e9
            total_memory = torch.cuda.mem_get_info()[1] / 1e9
            logger.debug(f"GPU memory: {free_memory:.2f}GB free / {total_memory:.2f}GB total")
    
    def _download_pdfs(self) -> List[Path]:
        """Download all PDFs from GCS"""
        pdf_files = []
        
        logger.info(f"Downloading PDFs from gs://{self.bucket_name}/{self.input_prefix}")
        
        for blob in self.bucket.list_blobs(prefix=self.input_prefix):
            if blob.name.lower().endswith('.pdf'):
                local_path = WORK_DIR / Path(blob.name).name
                
                try:
                    blob.download_to_filename(str(local_path))
                    pdf_files.append(local_path)
                    
                    size_mb = local_path.stat().st_size / 1e6
                    logger.info(f"  Downloaded: {local_path.name} ({size_mb:.1f}MB)")
                    
                except Exception as e:
                    logger.error(f"  Failed to download {blob.name}: {e}")
        
        return sorted(pdf_files)
    
    def _assess_pdf_risk(self, pdf_path: Path) -> str:
        """
        Assess PDF processing risk based on size and page count
        Returns: Risk level (LOW, MEDIUM, HIGH, or BLOCKED)
        """
        try:
            # Use context manager for proper resource cleanup
            with pdfium.PdfDocument(str(pdf_path)) as pdf:
                page_count = len(pdf)
                
                # Sample first page for size estimation
                if page_count > 0:
                    page = pdf[0]
                    width = page.get_width()
                    height = page.get_height()
                    megapixels = (width * height) / 1e6
                else:
                    megapixels = 0
                
                logger.info(f"  PDF analysis: {page_count} pages, first page {megapixels:.1f}MP")
                
                # Determine risk level based on characteristics
                if page_count > 1000:
                    logger.info(f"  Risk: HIGH (>1000 pages)")
                    return PDFRiskLevel.HIGH
                elif megapixels > 20 or page_count > 500:
                    logger.info(f"  Risk: MEDIUM (large pages or >500 pages)")
                    return PDFRiskLevel.MEDIUM
                else:
                    logger.info(f"  Risk: LOW (standard document)")
                    return PDFRiskLevel.LOW
                    
        except Exception as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypt" in error_msg:
                logger.error(f"  PDF is encrypted or password-protected")
                return PDFRiskLevel.BLOCKED
            else:
                logger.warning(f"  PDF validation error: {e}")
                # Assume high risk if we can't analyze
                return PDFRiskLevel.HIGH
    
    def _get_adaptive_batch_sizes(self, risk_level: str) -> List[int]:
        """
        Get batch sizes to try based on risk level and available GPU memory
        Returns: List of batch sizes to attempt in order
        """
        if not torch.cuda.is_available():
            return [1]
        
        # Check available GPU memory
        free_memory_gb = torch.cuda.mem_get_info()[0] / 1e9
        
        logger.info(f"  Available GPU memory: {free_memory_gb:.2f}GB")
        
        # Determine batch sizes based on risk and available memory
        if risk_level == PDFRiskLevel.HIGH or free_memory_gb < 4:
            return [1]
        elif risk_level == PDFRiskLevel.MEDIUM or free_memory_gb < 8:
            return [2, 1]
        else:  # LOW risk with sufficient memory
            return [3, 2, 1]
    
    def _process_pdf_adaptive(self, pdf_path: Path, risk_level: str) -> Dict[str, Any]:
        """
        Process PDF with adaptive batch sizing and memory management
        Returns: Processing result dictionary
        """
        batch_sizes = self._get_adaptive_batch_sizes(risk_level)
        
        result = {
            "pdf": pdf_path.name,
            "status": "failed",
            "batch_size": None,
            "processing_time": 0,
            "risk_level": risk_level
        }
        
        start_time = time.time()
        output_file = OUTPUT_DIR / f"{pdf_path.stem}.mmd"
        
        for batch_size in batch_sizes:
            try:
                logger.info(f"  Attempting with batch_size={batch_size}")
                
                # Build nougat command - FIXED: using --batchsize not --batch-size
                cmd = [
                    "nougat",
                    str(pdf_path),
                    "-o", str(OUTPUT_DIR),
                    "--batchsize", str(batch_size),  # CORRECT PARAMETER
                    "--markdown"
                ]
                
                # Add no-skipping for low-risk PDFs to improve accuracy
                if risk_level == PDFRiskLevel.LOW:
                    cmd.append("--no-skipping")
                
                logger.debug(f"  Command: {' '.join(cmd)}")
                
                # Run with proper process group for clean termination
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
                
                try:
                    stdout, stderr = process.communicate(timeout=PROCESSING_TIMEOUT)
                    returncode = process.returncode
                except subprocess.TimeoutExpired:
                    # Kill entire process group
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        time.sleep(5)
                        if process.poll() is None:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.terminate()
                        time.sleep(5)
                        if process.poll() is None:
                            process.kill()
                    
                    logger.warning(f"  Timeout after {PROCESSING_TIMEOUT/3600:.1f} hours")
                    result["status"] = "timeout"
                    self.stats["timeout"] += 1
                    break
                
                # Check for CUDA OOM
                if returncode != 0 and "CUDA out of memory" in stderr:
                    logger.warning(f"  CUDA OOM with batch_size={batch_size}")
                    self.stats["oom_errors"] += 1
                    # Clean memory and try smaller batch
                    self._cleanup_gpu_memory()
                    continue
                
                # Check for other errors
                if returncode != 0:
                    logger.error(f"  Nougat error (code {returncode}): {stderr[:500]}")
                    # Don't try smaller batch for non-OOM errors
                    result["error"] = f"Nougat failed with code {returncode}"
                    break
                
                # Check if output was created
                if output_file.exists() and output_file.stat().st_size > 0:
                    # Upload immediately to GCS
                    gcs_path = self._upload_output(output_file)
                    
                    result["status"] = "success"
                    result["batch_size"] = batch_size
                    result["gcs_path"] = gcs_path
                    result["output_size_mb"] = output_file.stat().st_size / 1e6
                    
                    # Delete local file to save space
                    output_file.unlink()
                    
                    logger.info(f"  ✓ Success with batch_size={batch_size}")
                    break
                else:
                    logger.warning(f"  No output generated with batch_size={batch_size}")
                    
            except Exception as e:
                logger.error(f"  Unexpected error: {e}")
                result["status"] = "error"
                result["error"] = str(e)
                break
            
            finally:
                # Always cleanup after each attempt
                self._cleanup_gpu_memory()
        
        result["processing_time"] = time.time() - start_time
        return result
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=2, min=4, max=60)
    )
    def _upload_output(self, local_file: Path) -> str:
        """
        Upload output file to GCS with exponential backoff retry
        Returns: GCS path of uploaded file
        """
        blob_name = f"{self.output_prefix}{local_file.name}"
        blob = self.bucket.blob(blob_name)
        
        # Use resumable upload for files > 5MB
        if local_file.stat().st_size > 5_000_000:
            blob.chunk_size = 5 * 1024 * 1024
        
        blob.upload_from_filename(str(local_file))
        
        gcs_path = f"gs://{self.bucket_name}/{blob_name}"
        logger.info(f"  Uploaded to: {gcs_path}")
        
        return gcs_path
    
    def _update_stats(self, result: Dict[str, Any]) -> None:
        """Update processing statistics based on result"""
        self.stats["total"] += 1
        status = result.get("status", "failed")
        
        if status == "success":
            self.stats["successful"] += 1
        elif status == "timeout":
            self.stats["timeout"] += 1
        elif status == "blocked":
            self.stats["blocked"] += 1
        else:
            self.stats["failed"] += 1
    
    def _create_manifest(self, results: List[Dict[str, Any]], start_time: float) -> Dict[str, Any]:
        """
        Create processing manifest with metadata
        Returns: Manifest dictionary
        """
        duration = time.time() - start_time
        
        manifest = {
            "job_id": os.environ.get("CLOUD_ML_JOB_ID", "local"),
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "duration_readable": f"{duration/3600:.1f} hours",
            "bucket": self.bucket_name,
            "input_prefix": self.input_prefix,
            "output_prefix": self.output_prefix,
            "summary": self.stats,
            "gpu_info": {
                "available": torch.cuda.is_available(),
                "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                "memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else None
            },
            "results": results
        }
        
        return manifest
    
    def _upload_manifest(self, manifest: Dict[str, Any]) -> None:
        """Save and upload manifest to GCS"""
        manifest_path = OUTPUT_DIR / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        try:
            blob_name = f"{self.output_prefix}manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_filename(str(manifest_path))
            logger.info(f"Manifest uploaded to: gs://{self.bucket_name}/{blob_name}")
        except Exception as e:
            logger.error(f"Failed to upload manifest: {e}")
            logger.info(f"Manifest saved locally at: {manifest_path}")
    
    def _report_final_status(self, manifest: Dict[str, Any]) -> None:
        """Report final processing status"""
        logger.info(f"\n{'='*60}")
        logger.info("PIPELINE COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total PDFs: {self.stats['total']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Timeout: {self.stats['timeout']}")
        logger.info(f"Blocked: {self.stats['blocked']}")
        logger.info(f"OOM Errors: {self.stats['oom_errors']}")
        logger.info(f"Duration: {manifest['duration_readable']}")
        logger.info(f"Output location: gs://{self.bucket_name}/{self.output_prefix}")
        logger.info(f"{'='*60}")


def main():
    """Main entry point"""
    try:
        processor = NougatProcessor()
        processor.run()
        
        # Exit with appropriate code
        if processor.stats["successful"] == processor.stats["total"]:
            sys.exit(0)
        else:
            sys.exit(1)  # Partial failure
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(2)  # Complete failure


if __name__ == "__main__":
    main()