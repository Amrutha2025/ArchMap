from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from app.api.routes.git_analysis import router as git_router
except Exception:
    git_router = None  # Router may not be ready during initial scaffolding

app = FastAPI(title="ArchMap Backend", version="0.1.0")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


if git_router is not None:
    app.include_router(git_router)
