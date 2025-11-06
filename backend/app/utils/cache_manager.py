from __future__ import annotations

import hashlib
import logging
import os
import shutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from git import Repo, InvalidGitRepositoryError, NoSuchPathError

logger = logging.getLogger(__name__)


class RepositoryCacheManager:
    """
    Thread-safe local cache manager for git repositories.
    Base cache path: ~/.archmap/repos or env GIT_CACHE_DIR
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        env_dir = os.getenv("GIT_CACHE_DIR")
        default_dir = Path.home() / ".archmap" / "repos"
        self.base_path: Path = Path(env_dir) if env_dir else (base_path or default_dir)
        self._lock = threading.RLock()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _hash_url(self, repo_url: str) -> str:
        return hashlib.sha256(repo_url.encode("utf-8")).hexdigest()[:16]

    def get_cache_path(self, repo_url: str) -> Path:
        with self._lock:
            h = self._hash_url(repo_url)
            return self.base_path / h

    def is_cached(self, repo_url: str) -> bool:
        p = self.get_cache_path(repo_url)
        exists = p.exists() and (p / ".git").exists()
        logger.debug("Cache exists for %s: %s", repo_url, exists)
        return exists

    def _validate_repo(self, path: Path) -> bool:
        try:
            repo = Repo(str(path))
            # simple command to validate health
            _ = repo.head.commit.hexsha  # access head commit
            return True
        except (InvalidGitRepositoryError, NoSuchPathError, Exception) as e:
            logger.warning("Repository at %s is invalid: %s", str(path), str(e))
            return False

    def get_cached_repo(self, repo_url: str) -> Optional[Repo]:
        with self._lock:
            p = self.get_cache_path(repo_url)
            if not p.exists():
                return None
            if not self._validate_repo(p):
                # Attempt cleanup if corrupted
                try:
                    shutil.rmtree(p, ignore_errors=True)
                except Exception as e:
                    logger.error("Failed to cleanup corrupted cache at %s: %s", str(p), str(e))
                return None
            try:
                return Repo(str(p))
            except Exception as e:
                logger.error("Failed to open cached repo at %s: %s", str(p), str(e))
                return None

    def cleanup_old_repos(self, days_old: int = 30) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        removed = 0
        with self._lock:
            for child in self.base_path.iterdir():
                try:
                    if not child.is_dir():
                        continue
                    mtime = datetime.utcfromtimestamp(child.stat().st_mtime)
                    if mtime < cutoff:
                        shutil.rmtree(child, ignore_errors=True)
                        removed += 1
                        logger.info("Removed old cached repo: %s", str(child))
                except Exception as e:
                    logger.error("Error during cleanup for %s: %s", str(child), str(e))
        return removed

    def get_cache_size(self) -> int:
        total = 0
        with self._lock:
            for root, dirs, files in os.walk(self.base_path):
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        total += os.path.getsize(fp)
                    except FileNotFoundError:
                        continue
                    except Exception as e:
                        logger.debug("Error calculating size for %s: %s", fp, str(e))
        return int(total / (1024 * 1024))

    def clear_all(self) -> None:
        with self._lock:
            try:
                if self.base_path.exists():
                    shutil.rmtree(self.base_path, ignore_errors=True)
                self.base_path.mkdir(parents=True, exist_ok=True)
                logger.info("Cleared entire cache directory: %s", str(self.base_path))
            except Exception as e:
                logger.error("Failed to clear cache directory: %s", str(e))

    def ensure_space_for_clone(self, required_mb: int = 600) -> None:
        """Check disk space before cloning; raises OSError if insufficient."""
        try:
            total, used, free = shutil.disk_usage(self.base_path)
            if free < required_mb * 1024 * 1024:
                raise OSError("Insufficient disk space in cache directory")
        except FileNotFoundError:
            self.base_path.mkdir(parents=True, exist_ok=True)
            total, used, free = shutil.disk_usage(self.base_path)
            if free < required_mb * 1024 * 1024:
                raise OSError("Insufficient disk space in cache directory")
