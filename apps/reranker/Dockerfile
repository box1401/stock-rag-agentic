FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models \
    TRANSFORMERS_CACHE=/models \
    SENTENCE_TRANSFORMERS_HOME=/models

ARG RERANKER_MODEL=BAAI/bge-reranker-v2-m3
ARG BAKE_MODEL=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install --extra-index-url https://download.pytorch.org/whl/cpu \
      torch==2.4.1 && \
    pip install \
      fastapi==0.115.5 \
      uvicorn[standard]==0.32.0 \
      sentence-transformers==3.3.0 \
      pydantic==2.9.2

# Pre-download model into image for fast Cloud Run cold-start
RUN if [ "$BAKE_MODEL" = "true" ]; then \
      python -c "from sentence_transformers import CrossEncoder; CrossEncoder('$RERANKER_MODEL', device='cpu', max_length=512)"; \
    fi

COPY app.py .

EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
