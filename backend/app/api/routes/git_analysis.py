from __future__ import annotations

import asyncio
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.schemas.git_analysis import (
    AnalysisResult,
    BusFactorAnalysis,
    CommitData,
    FileCouplingData,
    FileOwnershipData,
    RepositoryAnalysisRequest,
)
from app.services.git_analyzer import GitAnalyzer

router = APIRouter(prefix="/api/git", tags=["git-analysis"])

analyzer = GitAnalyzer()

_jobs: dict[UUID, AnalysisResult] = {}


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(request: RepositoryAnalysisRequest, background_tasks: BackgroundTasks):
    async def run_analysis():
        result = await analyzer.analyze_repository(request.url, depth=request.depth, token=request.token)
        _jobs[result.repository_id] = result

    background_tasks.add_task(run_analysis)
    # Minimal immediate response; in real impl, return job id
    dummy = await analyzer.analyze_repository(request.url, depth=request.depth, token=request.token)
    _jobs[dummy.repository_id] = dummy
    return dummy


@router.get("/repositories", response_model=List[dict])
async def list_repositories(skip: int = 0, limit: int = 50, sort_by: Optional[str] = Query(None)):
    # Placeholder: return in-memory jobs as repositories
    items = list(_jobs.values())[skip : skip + limit]
    return [
        {
            "id": str(r.repository_id),
            "status": r.status,
            "total_commits": r.total_commits,
            "total_files": r.total_files,
            "bus_factor": r.bus_factor,
        }
        for r in items
    ]


@router.get("/repositories/{repo_id}", response_model=dict)
async def get_repository(repo_id: UUID):
    if repo_id not in _jobs:
        raise HTTPException(status_code=404, detail="Not found")
    r = _jobs[repo_id]
    return r.dict()


@router.get("/repositories/{repo_id}/ownership", response_model=List[FileOwnershipData])
async def get_ownership(repo_id: UUID):
    if repo_id not in _jobs:
        raise HTTPException(status_code=404, detail="Not found")
    # Not stored per-file in-memory; return empty list placeholder
    return []


@router.get("/repositories/{repo_id}/coupling", response_model=List[FileCouplingData])
async def get_coupling(repo_id: UUID, min_score: float = 0.3, top_n: int = 50):
    if repo_id not in _jobs:
        raise HTTPException(status_code=404, detail="Not found")
    # Not stored per-file; return empty list placeholder
    return []


@router.get("/repositories/{repo_id}/bus-factor", response_model=BusFactorAnalysis)
async def get_bus_factor(repo_id: UUID):
    if repo_id not in _jobs:
        raise HTTPException(status_code=404, detail="Not found")
    r = _jobs[repo_id]
    return BusFactorAnalysis(
        bus_factor=r.bus_factor,
        risk_level="low",
        critical_developers=[],
        coverage_percentage=0.0,
    )


@router.get("/repositories/{repo_id}/commits", response_model=List[CommitData])
async def get_commits(repo_id: UUID):
    # Commit listing not persisted; return empty list placeholder
    return []


@router.delete("/repositories/{repo_id}")
async def delete_repository(repo_id: UUID):
    _jobs.pop(repo_id, None)
    return {"status": "deleted"}
