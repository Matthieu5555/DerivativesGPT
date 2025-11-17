from pathlib import Path
from google.cloud import aiplatform
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import Dict
import time

# Load environment from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configuration constants - these define the Vertex AI job parameters
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")  # Called by: aiplatform.init
GCP_REGION = os.getenv("GCP_REGION")  # Called by: aiplatform.init
OCR_GCP_BUCKET_NAME = os.getenv("OCR_GCP_BUCKET_NAME")  # Called by: create_environment_variables
CONTAINER_IMAGE = f"{GCP_REGION}-docker.pkg.dev/{GCP_PROJECT_ID}/nougat-ocr/nougat-processor:v1"  # Called by: submit_custom_job
MACHINE_TYPE = "n1-standard-4"  # Called by: submit_custom_job, 4 vCPU for T4
ACCELERATOR_TYPE = "NVIDIA_TESLA_T4"  # Called by: submit_custom_job
ACCELERATOR_COUNT = 1  # Called by: submit_custom_job


def validate_config() -> None:
    """
    Validates required configuration values are present.
    This ensures the script fails early if misconfigured.
    Called by: main function before job submission.
    """
    if not all([GCP_PROJECT_ID, GCP_REGION, OCR_GCP_BUCKET_NAME]):
        raise RuntimeError("Missing GCP_PROJECT_ID, GCP_REGION, or OCR_GCP_BUCKET_NAME in .env file")


def create_environment_variables(bucket_name: str) -> Dict[str, str]:
    """
    Creates environment variable dict for container.
    This passes configuration to the running container job.
    Called by: submit_custom_job to configure container environment.
    Returns: Dictionary of environment variable key-value pairs.
    """
    return {
        "BUCKET_NAME": bucket_name,
        "INPUT_PREFIX": "input/",
        "OUTPUT_PREFIX": "output/",
        "BATCH_SIZE": "6"
    }


def submit_custom_job(
    project_id: str,
    region: str,
    bucket_name: str,
    container_image: str
) -> str:
    """
    Submits GPU-enabled custom container job to Vertex AI.
    This creates and runs the Nougat OCR job on T4 GPU.
    Called by: main function after validation.
    Returns: Job display name for tracking.
    Raises: RuntimeError if job submission fails.
    """
    aiplatform.init(project=project_id, location=region)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job_name = f"nougat-ocr-{timestamp}"
    
    env_vars = create_environment_variables(bucket_name)
    
    print(f"Attempting to submit Vertex AI Custom Job:")
    print(f"  Name: {job_name}")
    print(f"  Container: {container_image}")
    print(f"  Machine: {MACHINE_TYPE}")
    print(f"  Accelerator: {ACCELERATOR_TYPE} x {ACCELERATOR_COUNT}")
    print(f"  Bucket: gs://{bucket_name}")
    print("")
    
    job = aiplatform.CustomContainerTrainingJob(
        display_name=job_name,
        container_uri=container_image,
        staging_bucket=f"gs://{bucket_name}"
    )
    
    print("Submitting job (this may take 10-15 seconds)...")
    
    try:
        job.run(
            replica_count=1,
            machine_type=MACHINE_TYPE,
            accelerator_type=ACCELERATOR_TYPE,
            accelerator_count=ACCELERATOR_COUNT,
            environment_variables=env_vars,
            sync=False
        )
    except Exception as e:
        raise RuntimeError(f"Job submission failed: {e}")
    
    print(f"✓ Job submission call completed")
    print(f"  Display name: {job_name}")
    print("")
    
    return job_name


def verify_job_created(project_id: str, region: str, job_name: str, max_attempts: int = 6) -> bool:
    """
    Verifies the job was created by polling the API.
    Since job creation is async, we poll for up to 30 seconds.
    Called by: main function after job submission.
    Returns: True if job found, False otherwise.
    """
    aiplatform.init(project=project_id, location=region)
    
    print(f"Verifying job '{job_name}' was created...")
    
    for attempt in range(max_attempts):
        print(f"  Attempt {attempt + 1}/{max_attempts}...", end=" ")
        
        try:
            jobs = aiplatform.CustomJob.list(
                filter=f'display_name="{job_name}"',
                location=region,
                project=project_id
            )
            
            if jobs:
                job = jobs[0]
                print(f"✓ Found! State: {job.state}")
                print(f"  Resource: {job.resource_name}")
                return True
            else:
                print("not found yet")
                
        except Exception as e:
            print(f"error: {e}")
        
        if attempt < max_attempts - 1:
            time.sleep(5)
    
    return False


def main() -> None:
    """
    Entry point for submitting the Vertex AI Custom Job.
    This validates configuration and submits the GPU-enabled OCR job.
    """
    validate_config()
    
    print(f"Configuration:")
    print(f"  Project: {GCP_PROJECT_ID}")
    print(f"  Region: {GCP_REGION}")
    print(f"  Bucket: {OCR_GCP_BUCKET_NAME}")
    print("")
    
    job_name = submit_custom_job(GCP_PROJECT_ID, GCP_REGION, OCR_GCP_BUCKET_NAME, CONTAINER_IMAGE)
    
    if verify_job_created(GCP_PROJECT_ID, GCP_REGION, job_name):
        print("")
        print(f"✓ Job successfully submitted and verified!")
        print(f"Monitor at: https://console.cloud.google.com/vertex-ai/training/custom-jobs?project={GCP_PROJECT_ID}")
        print(f"Results will appear at: gs://{OCR_GCP_BUCKET_NAME}/output/")
        print("")
        print(f"Check status with:")
        print(f"  gcloud ai custom-jobs list --region={GCP_REGION} --filter=\"displayName:{job_name}\"")
        print("")
        print(f"Stream logs with:")
        print(f"  gcloud ai custom-jobs stream-logs <JOB_ID> --region={GCP_REGION}")
    else:
        print("")
        print("WARNING: Job submission completed but job not found in list after 30 seconds")
        print("This may indicate a problem. Check the console:")
        print(f"  https://console.cloud.google.com/vertex-ai/training/custom-jobs?project={GCP_PROJECT_ID}")


if __name__ == "__main__":
    main()