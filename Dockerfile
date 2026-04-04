# RTLRepair-Env Dockerfile
# Build: docker build -t rtlrepair-env .
# Run:   docker run -p 7860:7860 rtlrepair-env

FROM ghcr.io/meta-pytorch/openenv-base:latest

# Install iverilog — the ONLY external dependency for grading (~50MB)
# This is what makes the grader deterministic and self-contained
RUN apt-get update && \
    apt-get install -y --no-install-recommends iverilog && \
    rm -rf /var/lib/apt/lists/*

# Verify iverilog is available
RUN iverilog --version

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy all project files
COPY . .

# Expose HF Spaces default port
EXPOSE 7860

# Health check — validator pings /reset
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f -X POST http://localhost:7860/reset || exit 1

# Start server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2"]