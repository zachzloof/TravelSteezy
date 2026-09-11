"""FastAPI application entry point.

One Railway service serves both the API and the built Vue frontend, so there is a
single public URL with no cross-origin configuration for a visitor to get wrong.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import REPO_ROOT, settings
from backend.db import init_db
from backend.rag import embeddings
from backend.rag import store as rag_store
from backend.routers import admin, auth, chat, profile
from backend.tracing.langfuse_setup import flush, tracing_enabled

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("onward")

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.ensure_dirs()
    init_db()
    logger.info("Onward starting up")
    logger.info("  database        : %s", settings.db_path)
    logger.info("  llm             : %s", settings.llm_model if settings.llm_enabled else "DISABLED")
    logger.info("  rag backend     : %s", rag_store.backend_name())
    logger.info("  embeddings      : %s", embeddings.embedding_backend())
    logger.info("  langfuse        : %s", "on" if tracing_enabled() else "off")
    logger.info("  admin configured: %s", bool(settings.admin_password))
    logger.info("  auto-approve    : %s", settings.admin_auto_approve)
    yield
    flush()


app = FastAPI(
    title="Onward",
    description="A multi-agent travel assistant for long-term backpackers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(profile.router)
app.include_router(chat.router)


@app.get("/health", tags=["meta"])
def health() -> JSONResponse:
    """Honest status of every dependency.

    Deliberately reports which services are real and which are on their fallback
    path, so the README's claims can be checked against the running deployment.
    """
    return JSONResponse(
        {
            "status": "ok",
            "database": {"path": str(settings.db_path), "exists": settings.db_path.exists()},
            "llm": {"enabled": settings.llm_enabled, "model": settings.llm_model},
            "rag": {
                "backend": rag_store.backend_name(),
                "embeddings": embeddings.embedding_backend(),
                "pinecone_configured": settings.pinecone_enabled,
            },
            "tracing": {"langfuse": tracing_enabled()},
            "auth": {
                "admin_configured": bool(settings.admin_password),
                "auto_approve": settings.admin_auto_approve,
            },
        }
    )


# --------------------------------------------------------------------------- #
# static frontend
# --------------------------------------------------------------------------- #
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

if settings.serve_frontend and FRONTEND_DIST.exists():
    app.mount(
        "/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets"
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        """Serve the SPA, letting Vue Router own client-side paths."""
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

else:

    @app.get("/", include_in_schema=False)
    def root() -> JSONResponse:
        return JSONResponse(
            {
                "app": "Onward",
                "note": "Frontend not built. Run `npm run build` in frontend/.",
                "docs": "/docs",
                "health": "/health",
            }
        )
