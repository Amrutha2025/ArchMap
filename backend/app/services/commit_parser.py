from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from git import Repo
from git.objects.commit import Commit as GitCommit

from app.schemas.git_analysis import CommitData

logger = logging.getLogger(__name__)

BUG_KEYWORDS = {
    "fix",
    "fixed",
    "fixes",
    "fixing",
    "bug",
    "bugs",
    "bugfix",
    "error",
    "errors",
    "defect",
    "defects",
    "issue",
    "issues",
    "patch",
    "patched",
    "resolve",
    "resolved",
    "resolves",
}

ISSUE_PATTERNS = [
    re.compile(r"#\d+"),
    re.compile(r"[A-Z]+-\d+"),
    re.compile(r"GH-\d+"),
]


class CommitParser:
    def __init__(self) -> None:
        self._commit_cache: dict[str, CommitData] = {}

    def detect_bug_fix_commit(self, message: str) -> bool:
        m = message.lower()
        if any(k in m for k in BUG_KEYWORDS):
            return True
        for pat in ISSUE_PATTERNS:
            if pat.search(message):
                return True
        return False

    def parse_changed_files(self, commit: GitCommit) -> tuple[int, int, int]:
        try:
            stats = commit.stats.total
            files_changed = stats.get("files", 0)
            lines_added = stats.get("insertions", 0)
            lines_deleted = stats.get("deletions", 0)
            return files_changed, lines_added, lines_deleted
        except Exception:
            return 0, 0, 0

    def parse_commit(self, commit: GitCommit) -> CommitData:
        if commit.hexsha in self._commit_cache:
            return self._commit_cache[commit.hexsha]
        files_changed, lines_added, lines_deleted = self.parse_changed_files(commit)
        data = CommitData(
            hash=commit.hexsha,
            author=getattr(commit.author, "name", "") or "",
            email=getattr(commit.author, "email", "") or "",
            date=datetime.utcfromtimestamp(commit.committed_date),
            message=commit.message or "",
            is_bug_fix=self.detect_bug_fix_commit(commit.message or ""),
            files_changed=files_changed,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
        )
        self._commit_cache[commit.hexsha] = data
        return data

    def calculate_commit_frequency(self, repo: Repo, file_path: str, months: int = 6) -> int:
        since = datetime.utcnow() - timedelta(days=months * 30)
        count = 0
        for c in repo.iter_commits(paths=file_path, since=since.isoformat()):
            count += 1
        return count

    def get_commits_in_date_range(self, repo: Repo, start_date: datetime, end_date: datetime) -> List[GitCommit]:
        commits: List[GitCommit] = []
        for c in repo.iter_commits(since=start_date.isoformat(), until=end_date.isoformat()):
            commits.append(c)
        commits.sort(key=lambda x: x.committed_datetime)
        return commits

    def build_change_index(self, repo: Repo, max_commits: Optional[int] = None) -> dict[str, set[str]]:
        file_changes: dict[str, set[str]] = defaultdict(set)
        it = repo.iter_commits()
        if max_commits:
            it = list(it)[:max_commits]
        for c in it:
            try:
                for f in c.stats.files.keys():
                    file_changes[f].add(c.hexsha)
            except Exception:
                continue
        return file_changes
