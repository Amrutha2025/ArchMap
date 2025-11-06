from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from git import Repo, GitCommandError

from app.schemas.git_analysis import FileOwnershipData, OwnerData, BusFactorAnalysis

logger = logging.getLogger(__name__)


class OwnershipCalculator:
    def __init__(self) -> None:
        self._blame_cache: dict[tuple[str, str], Dict[str, int]] = {}

    def _safe_blame(self, repo: Repo, rev: str, file_path: str) -> List[tuple]:
        try:
            return repo.blame(rev, file_path)
        except GitCommandError as e:
            logger.warning("Blame failed for %s: %s", file_path, str(e))
            return []
        except Exception as e:
            logger.error("Unexpected blame error for %s: %s", file_path, str(e))
            return []

    def _aggregate_blame(self, blame_chunks: List[tuple]) -> Dict[str, int]:
        lines_by_author: Dict[str, int] = Counter()
        for commit, lines in blame_chunks:
            email = getattr(commit.author, "email", "") or "unknown"
            lines_by_author[email] += len(lines)
        return dict(lines_by_author)

    def _last_commit_per_author(self, blame_chunks: List[tuple]) -> Dict[str, datetime]:
        last_dates: Dict[str, datetime] = {}
        for commit, lines in blame_chunks:
            email = getattr(commit.author, "email", "") or "unknown"
            dt = datetime.utcfromtimestamp(commit.committed_date)
            if email not in last_dates or dt > last_dates[email]:
                last_dates[email] = dt
        return last_dates

    def calculate_file_ownership(self, repo: Repo, file_path: str) -> FileOwnershipData:
        key = (repo.working_tree_dir or "", file_path)
        if key in self._blame_cache:
            blame_data = self._blame_cache[key]
            last_dates = {}
        else:
            blame_chunks = self._safe_blame(repo, "HEAD", file_path)
            blame_data = self._aggregate_blame(blame_chunks)
            last_dates = self._last_commit_per_author(blame_chunks)
            self._blame_cache[key] = blame_data
        total_lines = max(sum(blame_data.values()), 1)
        owners: List[OwnerData] = []
        primary_owner: Optional[OwnerData] = None
        for email, lines in sorted(blame_data.items(), key=lambda x: x[1], reverse=True):
            percentage = (lines / total_lines) * 100.0
            od = OwnerData(
                name=email.split("@")[0],
                email=email,
                lines=lines,
                percentage=percentage,
                last_commit=last_dates.get(email, datetime.min),
            )
            owners.append(od)
        if owners and owners[0].percentage > 50.0:
            primary_owner = owners[0]
        last_modified = max((o.last_commit for o in owners if o.last_commit), default=datetime.min)
        return FileOwnershipData(
            file_path=file_path,
            owners=owners,
            primary_owner=primary_owner,
            total_lines=total_lines,
            last_modified=last_modified,
        )

    def calculate_bus_factor(self, repo: Repo, file_paths: List[str]) -> BusFactorAnalysis:
        contribution: Dict[str, int] = defaultdict(int)
        total = 0
        for fp in file_paths:
            fo = self.calculate_file_ownership(repo, fp)
            total += fo.total_lines
            for o in fo.owners:
                contribution[o.email] += o.lines
        sorted_contrib = sorted(contribution.items(), key=lambda x: x[1], reverse=True)
        cumulative = 0
        count = 0
        critical = []
        for email, lines in sorted_contrib:
            cumulative += lines
            count += 1
            critical.append(email)
            if total > 0 and cumulative / total >= 0.5:
                break
        coverage = (cumulative / total * 100.0) if total > 0 else 0.0
        risk_level = "low"
        if count <= 1:
            risk_level = "critical"
        elif count == 2:
            risk_level = "high"
        elif count == 3:
            risk_level = "medium"
        return BusFactorAnalysis(
            bus_factor=count,
            risk_level=risk_level,
            critical_developers=critical,
            coverage_percentage=coverage,
        )

    def detect_orphaned_files(self, repo: Repo, file_paths: List[str], inactive_days: int = 180) -> List[str]:
        threshold = datetime.utcnow() - timedelta(days=inactive_days)
        orphans: List[str] = []
        for fp in file_paths:
            fo = self.calculate_file_ownership(repo, fp)
            if fo.primary_owner and fo.primary_owner.last_commit < threshold:
                orphans.append(fp)
        return orphans

    def calculate_knowledge_concentration(self, ownership_data: List[FileOwnershipData]) -> float:
        # Gini coefficient across all files/authors based on lines
        contributions: List[int] = []
        for fo in ownership_data:
            contributions.extend([o.lines for o in fo.owners])
        if not contributions:
            return 0.0
        contributions.sort()
        n = len(contributions)
        cum = 0
        for i, x in enumerate(contributions, start=1):
            cum += i * x
        total = sum(contributions)
        gini = (2 * cum) / (n * total) - (n + 1) / n
        return max(0.0, min(1.0, gini))

    def get_author_activity_timeline(self, repo: Repo, author: str, months: int = 12) -> List[dict]:
        start = datetime.utcnow() - timedelta(days=months * 30)
        counts: Dict[str, int] = defaultdict(int)
        for c in repo.iter_commits(since=start.isoformat(), author=author):
            dt = c.committed_datetime
            bucket = f"{dt.year}-{dt.month:02d}"
            counts[bucket] += 1
        series = []
        for i in range(months):
            d = start + timedelta(days=i * 30)
            key = f"{d.year}-{d.month:02d}"
            series.append({"month": key, "count": counts.get(key, 0)})
        return series
