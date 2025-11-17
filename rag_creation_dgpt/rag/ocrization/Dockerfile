FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    poppler-utils \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create model cache directory with proper permissions
RUN mkdir -p /root/.cache/huggingface && \
    mkdir -p /root/.cache/torch && \
    chmod -R 777 /root/.cache

# Copy requirements and install
COPY ocr_docker_requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Nougat model to avoid runtime download delays
RUN python -c "from nougat import NougatModel; from nougat.utils.checkpoint import get_checkpoint; get_checkpoint(None, model_tag='0.1.0-base')" || echo "Model pre-download skipped, will download at runtime"

# Copy application code
COPY process_pdfs.py .

# Ensure unbuffered output for Vertex AI logging
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface
ENV TORCH_HOME=/root/.cache/torch
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512

# Add startup diagnostics
CMD ["/bin/bash", "-c", "echo 'Container starting at' $(date) && \
    echo 'Python version:' $(python --version) && \
    echo 'Checking GPU...' && \
    python -c \"import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \\\"No GPU\\\"}'); print(f'CUDA version: {torch.version.cuda}');\" && \
    echo 'Checking Nougat installation...' && \
    python -c \"from nougat import NougatModel; print('Nougat imported successfully')\" && \
    echo 'Cache directories:' && \
    ls -la /root/.cache/ 2>&1 || echo 'Cache directory check failed' && \
    echo 'Starting process_pdfs.py...' && \
    python -u process_pdfs.py"]