"""
Entry point for the VPC Management API.

Run locally:
    uvicorn app.main:app --reload

Interactive docs available at:
    http://localhost:8000/docs  (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

import logging

from fastapi import FastAPI

from app.apis.auth import router as auth_router
from app.apis.vpc import router as vpc_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="VPC Management API",
    description=(
        "REST API to create AWS VPCs. All endpoints (except `/auth/token`) require a valid JWT "
        "Bearer token."
    ),
    version="1.0.0",
    contact={"name": "Platform Engineering"},
    license_info={"name": "MIT"},
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(vpc_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Health check")
def health() -> dict:
    """Returns 200 OK when the service is running."""
    return {"status": "ok"}
