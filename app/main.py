import os
import json
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

logging.basicConfig(level=LOG_LEVEL, format="%(message)s")
logger = logging.getLogger("devops-app")

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors"
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["endpoint"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(json.dumps({
        "level": "INFO",
        "message": "Application started",
        "environment": ENVIRONMENT,
        "version": APP_VERSION
    }))
    yield
    logger.info(json.dumps({
        "level": "INFO",
        "message": "Application shutting down"
    }))


app = FastAPI(
    title="DevOps Assessment Application",
    version=APP_VERSION,
    lifespan=lifespan
)


@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response

    except Exception:
        raise

    finally:
        duration = time.perf_counter() - start
        endpoint = request.url.path

        REQUEST_COUNT.labels(
            request.method,
            endpoint,
            str(status_code)
        ).inc()

        REQUEST_LATENCY.labels(endpoint).observe(duration)

        if status_code >= 400:
            ERROR_COUNT.inc()

        logger.info(json.dumps({
            "level": "INFO" if status_code < 400 else "ERROR",
            "method": request.method,
            "path": endpoint,
            "status": status_code,
            "latency_seconds": round(duration, 5),
            "environment": ENVIRONMENT
        }))


@app.get("/")
async def root():
    return {
        "message": "Hello from DevOps Task!",
        "status": "running",
        "version": APP_VERSION
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": APP_VERSION
    }


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
