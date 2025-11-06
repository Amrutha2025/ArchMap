from __future__ import annotations

import os
import re
import time
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse

from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError

logger = logging.getLogger(__name__)

_GITHUB_PATTERN_HTTPS = re.compile(r"^https://(www\.)?github\.com/[^/]+/[^/]+(\.git)?/?$")
_GITLAB_PATTERN_HTTPS = re.compile(r"^https://(www\.)?gitlab\.com/[^/]+/[^/]+(\.git)?/?$")
_BITBUCKET_PATTERN_HTTPS = re.compile(r"^https://(www\.)?bitbucket\.org/[^/]+/[^/]+(\.git)?/?$")

_SSH_PATTERN = re.compile(r"^(git@|ssh://git@)(github\.com|gitlab\.com|bitbucket\.org)[:/][^/]+/[^/]+(\.git)?/?$")

BUG_PLATFORMS = {
    "github": {
        "host": "github.com",
        "https": _GITHUB_PATTERN_HTTPS,
    },
    "gitlab": {
        "host": "gitlab.com",
        "https": _GITLAB_PATTERN_HTTPS,
    },
    "bitbucket": {
        "host": "bitbucket.org",
        "https": _BITBUCKET_PATTERN_HTTPS,
    },
}


def _retry(func):
    def wrapper(*args, **kwargs):
        attempts = 3
        delay = 1.0
        for i in range(attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == attempts - 1:
                    raise
                time.sleep(delay)
                delay *= 2
    return wrapper


def validate_repository_url(url: str) -> bool:
    if not url:
        return False
    if _SSH_PATTERN.match(url):
        return True
    for p in BUG_PLATFORMS.values():
        if p["https"].match(url):
            return True
    try:
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https", "ssh", "git"} and parsed.netloc:
            return True
    except Exception:
        return False
    return False


def extract_repo_info(url: str) -> Dict[str, str]:
    if not validate_repository_url(url):
        raise ValueError("Invalid repository URL")
    platform = "unknown"
    if _SSH_PATTERN.match(url):
        host = _SSH_PATTERN.match(url).group(2)  # type: ignore
    else:
        host = urlparse(url).netloc
    for name, data in BUG_PLATFORMS.items():
        if data["host"] == host:
            platform = name
            break
    if _SSH_PATTERN.match(url):
        parts = re.split(r"[:/]", url)
        owner = parts[-2]
        repo = parts[-1]
    else:
        path = urlparse(url).path.strip("/")
        parts = path.split("/")
        owner = parts[0] if len(parts) > 0 else ""
        repo = parts[1] if len(parts) > 1 else ""
    if repo.endswith(".git"):
        repo = repo[:-4]
    return {"owner": owner, "repo": repo, "platform": platform}


def _mask_token(u: str) -> str:
    try:
        parsed = urlparse(u)
        if parsed.password:
            return u.replace(parsed.password, "***")
        if parsed.username and "token" in (parsed.username or ""):
            return u.replace(parsed.username, "token***")
    except Exception:
        pass
    return u


def _prepare_https_url_with_token(url: str, token: Optional[str]) -> str:
    if not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return url
    netloc = parsed.netloc
    if "@" in netloc:
        return url
    return f"https://{token}:x-oauth-basic@{netloc}{parsed.path}"


def _ensure_disk_space(path: Path, required_mb: int = 600) -> None:
    try:
        total, used, free = shutil.disk_usage(path)
        if free < required_mb * 1024 * 1024:
            raise OSError("Insufficient disk space for cloning")
    except FileNotFoundError:
        parent = path.parent if path.is_file() else path
        parent.mkdir(parents=True, exist_ok=True)
        total, used, free = shutil.disk_usage(parent)
        if free < required_mb * 1024 * 1024:
            raise OSError("Insufficient disk space for cloning")


@_retry
def clone_repository(url: str, local_path: Path, token: Optional[str] = None) -> Repo:
    if not validate_repository_url(url):
        raise ValueError("Invalid repository URL")
    _ensure_disk_space(local_path)
    local_path = Path(local_path)
    local_path.mkdir(parents=True, exist_ok=True)
    clone_url = url
    if url.startswith("http"):
        env_token = os.getenv("GITHUB_TOKEN")
        clone_url = _prepare_https_url_with_token(url, token or env_token)
    try:
        logger.info("Cloning repository %s into %s", _mask_token(clone_url), str(local_path))
        repo = Repo.clone_from(clone_url, str(local_path), depth=50, no_single_branch=True)
        return repo
    except GitCommandError as e:
        logger.error("Git clone failed: %s", str(e))
        raise


@_retry
def fetch_full_history(repo: Repo) -> None:
    try:
        g = repo.git
        try:
            g.fetch("--all", "--tags")
        except GitCommandError:
            pass
        try:
            g.fetch("--unshallow")
        except GitCommandError:
            pass
        try:
            g.fetch("origin", "--prune")
        except GitCommandError:
            pass
    except Exception as e:
        logger.error("Failed to fetch full history: %s", str(e))
        raise


def open_repository(path: Path) -> Repo:
    try:
        return Repo(str(path))
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        raise e
