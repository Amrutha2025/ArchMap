from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class RepositoryAnalysisRequest(BaseModel):
    url: HttpUrl
    depth: Literal["quick", "full"] = "full"
    analyze_ownership: bool = True
    analyze_coupling: bool = True
    token: Optional[str] = None


class OwnershipAnalysisRequest(BaseModel):
    file_paths: Optional[List[str]] = None
    inactive_days: int = 180


class CommitData(BaseModel):
    hash: str
    author: str
    email: str
    date: datetime
    message: str
    is_bug_fix: bool
    files_changed: int
    lines_added: int
    lines_deleted: int


class OwnerData(BaseModel):
    name: str
    email: str
    lines: int
    percentage: float
    last_commit: datetime


class FileOwnershipData(BaseModel):
    file_path: str
    owners: List[OwnerData]
    primary_owner: Optional[OwnerData]
    total_lines: int
    last_modified: datetime


class FileCouplingData(BaseModel):
    file_a: str
    file_b: str
    coupling_score: float
    times_together: int
    confidence: float


class BusFactorAnalysis(BaseModel):
    bus_factor: int
    risk_level: Literal["low", "medium", "high", "critical"]
    critical_developers: List[str]
    coverage_percentage: float


class AnalysisResult(BaseModel):
    repository_id: UUID
    status: str
    total_commits: int
    total_files: int
    total_authors: int
    bus_factor: int
    orphaned_files: int
    high_coupling_pairs: int
    analysis_duration_seconds: int
    completed_at: datetime
