
# Stage 1: Build dependencies
FROM python:3.14.4-slim-bookworm AS builder

WORKDIR /build

COPY app/requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Production image
FROM python:3.14.4-slim-bookworm AS production

LABEL org.opencontainers.image.title="DevOps Assessment API"
LABEL org.opencontainers.image.description="Production-ready DevOps assessment application"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="Care Guide Assessment"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV LOG_LEVEL=INFO
ENV ENVIRONMENT=production
ENV APP_VERSION=1.0.0

WORKDIR /app

# Install dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/

# Create non-root user
RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid appgroup \
    --no-create-home --shell /usr/sbin/nologin appuser

USER 10001:10001

EXPOSE 8000

# Container health check
HEALTHCHECK --interval=30s --timeout=5s \
    --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT','8000') + '/health', timeout=3)" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
