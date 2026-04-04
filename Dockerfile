# RTLRepair-Env Dockerfile
FROM ghcr.io/meta-pytorch/openenv-base:latest

# Install iverilog and curl for health check
RUN apt-get update && \
    apt-get install -y --no-install-recommends iverilog curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all project files
COPY . .

# Install the package and its dependencies using the root pyproject.toml
RUN pip install --no-cache-dir .

# Expose HF Spaces default port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f -X POST http://localhost:7860/reset || exit 1

# Start server — note uvicorn needs the package path
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]