from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from uuid import UUID, uuid4

from git import Repo

from app.schemas.git_analysis import AnalysisResult
from app.services.commit_parser import CommitParser
from app.services.coupling_analyzer import CouplingAnalyzer
from app.services.ownership_calculator import OwnershipCalculator
from app.utils.cache_manager import RepositoryCacheManager
from app.utils.git_helpers import clone_repository, extract_repo_info, fetch_full_history

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    step: str
    progress: int
    message: str = ""


class GitAnalyzer:
    def __init__(self, cache: Optional[RepositoryCacheManager] = None) -> None:
        self.cache = cache or RepositoryCacheManager()
        self.commit_parser = CommitParser()
        self.ownership_calc = OwnershipCalculator()
        self.coupling_analyzer = CouplingAnalyzer()

    async def analyze_repository(
        self,
        repo_url: str,
        depth: str = "full",
        token: Optional[str] = None,
        on_progress: Optional[Callable[[ProgressEvent], None]] = None,
    ) -> AnalysisResult:
        start = time.time()
        repo_id = uuid4()
        def emit(step: str, progress: int, message: str = ""):
            if on_progress:
                on_progress(ProgressEvent(step=step, progress=progress, message=message))

        emit("clone", 5, "Starting clone")
        self.cache.ensure_space_for_clone()
        cache_path = self.cache.get_cache_path(repo_url)
        repo_info = extract_repo_info(repo_url)
        repo: Repo
        if self.cache.is_cached(repo_url):
            repo = self.cache.get_cached_repo(repo_url)  # type: ignore
            if repo is None:
                repo = clone_repository(repo_url, cache_path, token)
        else:
            repo = clone_repository(repo_url, cache_path, token)
        emit("fetch", 10, "Fetching full history")
        await asyncio.to_thread(fetch_full_history, repo)

        max_commits = None if depth == "full" else 100
        emit("parse_commits", 20, "Parsing commits")
        commits = await asyncio.to_thread(lambda: list(repo.iter_commits(max_count=max_commits)))
        total_commits = len(commits)

        emit("ownership_list_files", 40, "Listing files")
        files = [str(p) for p in Path(repo.working_tree_dir or ".").rglob("*") if (Path(p).is_file() and ".git" not in str(p))]
        total_files = len(files)

        emit("ownership", 55, "Calculating ownership")
        ownership_results = await asyncio.gather(*[asyncio.to_thread(self.ownership_calc.calculate_file_ownership, repo, f) for f in files])

        emit("coupling", 75, "Detecting coupling")
        coupling_results = await asyncio.to_thread(self.coupling_analyzer.calculate_file_coupling, repo, 0.3, max_commits)

        emit("bus_factor", 85, "Calculating bus factor")
        bus = await asyncio.to_thread(self.ownership_calc.calculate_bus_factor, repo, files)

        emit("finalize", 95, "Finalizing")
        high_coupling_pairs = sum(1 for c in coupling_results if c.coupling_score >= 0.6)
        orphaned_files = len(self.ownership_calc.detect_orphaned_files(repo, files))

        duration = int(time.time() - start)
        emit("complete", 100, "Completed")
        return AnalysisResult(
            repository_id=repo_id,
            status="completed",
            total_commits=total_commits,
            total_files=total_files,
            total_authors=len({o.email for fo in ownership_results for o in fo.owners}),
            bus_factor=bus.bus_factor,
            orphaned_files=orphaned_files,
            high_coupling_pairs=high_coupling_pairs,
            analysis_duration_seconds=duration,
            completed_at=datetime.utcnow(),
        )

    async def update_analysis(self, repo_id: int) -> AnalysisResult:
        # Placeholder for incremental updates
        raise NotImplementedError

    async def get_analysis_summary(self, repo_id: int) -> dict:
        # Placeholder for stored summary retrieval
        raise NotImplementedError
