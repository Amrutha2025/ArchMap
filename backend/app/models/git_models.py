from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    Boolean,
    Enum,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
    CheckConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CloneStatus(str, enum.Enum):
    pending = "pending"
    cloning = "cloning"
    completed = "completed"
    failed = "failed"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ChangeType(str, enum.Enum):
    added = "added"
    modified = "modified"
    deleted = "deleted"
    renamed = "renamed"


class GitRepository(Base):
    __tablename__ = "git_repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(512), unique=True, nullable=False)
    owner = Column(String(256), nullable=True)
    name = Column(String(256), nullable=True)
    platform = Column(String(64), nullable=True)
    clone_status = Column(Enum(CloneStatus), nullable=False, default=CloneStatus.pending)
    last_analyzed = Column(DateTime, nullable=True)
    last_commit_hash = Column(String(64), nullable=True)
    total_commits = Column(Integer, nullable=False, default=0)
    total_files = Column(Integer, nullable=False, default=0)
    primary_language = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    commits = relationship("GitCommit", back_populates="repository", cascade="all, delete-orphan")
    authors = relationship("Author", back_populates="repository", cascade="all, delete-orphan")
    ownerships = relationship("FileOwnership", back_populates="repository", cascade="all, delete-orphan")
    couplings = relationship("FileCoupling", back_populates="repository", cascade="all, delete-orphan")
    jobs = relationship("AnalysisJob", back_populates="repository", cascade="all, delete-orphan")


class GitCommit(Base):
    __tablename__ = "git_commits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("git_repositories.id", ondelete="CASCADE"), nullable=False)
    commit_hash = Column(String(64), nullable=False)
    author_name = Column(String(256), nullable=True)
    author_email = Column(String(256), nullable=True)
    committer_name = Column(String(256), nullable=True)
    committer_email = Column(String(256), nullable=True)
    commit_date = Column(DateTime, nullable=False)
    message = Column(Text, nullable=True)
    is_bug_fix = Column(Boolean, nullable=False, default=False)
    files_changed = Column(Integer, nullable=False, default=0)
    lines_added = Column(Integer, nullable=False, default=0)
    lines_deleted = Column(Integer, nullable=False, default=0)
    parent_hashes = Column(ARRAY(String), nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("repository_id", "commit_hash", name="uq_repo_commit"),
        Index("ix_commit_repo_date", "repository_id", "commit_date"),
        Index("ix_commit_author_date", "author_email", "commit_date"),
        Index("ix_commit_hash", "commit_hash"),
    )

    repository = relationship("GitRepository", back_populates="commits")
    file_changes = relationship("FileChange", back_populates="commit", cascade="all, delete-orphan")


class FileChange(Base):
    __tablename__ = "file_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commit_id = Column(UUID(as_uuid=True), ForeignKey("git_commits.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(1024), nullable=False)
    change_type = Column(Enum(ChangeType), nullable=False)
    old_path = Column(String(1024), nullable=True)
    lines_added = Column(Integer, nullable=False, default=0)
    lines_deleted = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_filechange_commit_path", "commit_id", "file_path"),
        Index("ix_filechange_path", "file_path"),
    )

    commit = relationship("GitCommit", back_populates="file_changes")


class Author(Base):
    __tablename__ = "authors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("git_repositories.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(256), nullable=False)
    name = Column(String(256), nullable=True)
    aliases = Column(ARRAY(String), nullable=False, default=list)
    total_commits = Column(Integer, nullable=False, default=0)
    total_lines_added = Column(Integer, nullable=False, default=0)
    total_lines_deleted = Column(Integer, nullable=False, default=0)
    first_commit_date = Column(DateTime, nullable=True)
    last_commit_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("repository_id", "email", name="uq_author_repo_email"),
        Index("ix_author_repo_email", "repository_id", "email"),
    )

    repository = relationship("GitRepository", back_populates="authors")
    ownerships = relationship("FileOwnership", back_populates="author", cascade="all, delete-orphan")


class FileOwnership(Base):
    __tablename__ = "file_ownerships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("git_repositories.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(1024), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("authors.id", ondelete="CASCADE"), nullable=False)
    lines_owned = Column(Integer, nullable=False, default=0)
    ownership_percentage = Column(Float, nullable=False, default=0.0)
    is_primary_owner = Column(Boolean, nullable=False, default=False)
    last_modified_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("repository_id", "file_path", "author_id", name="uq_fileownership_unique"),
        Index("ix_fileownership_repo_path", "repository_id", "file_path"),
        Index("ix_fileownership_repo_author", "repository_id", "author_id"),
    )

    repository = relationship("GitRepository", back_populates="ownerships")
    author = relationship("Author", back_populates="ownerships")


class FileCoupling(Base):
    __tablename__ = "file_couplings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("git_repositories.id", ondelete="CASCADE"), nullable=False)
    file_path_a = Column(String(1024), nullable=False)
    file_path_b = Column(String(1024), nullable=False)
    coupling_score = Column(Float, nullable=False)
    times_changed_together = Column(Integer, nullable=False, default=0)
    total_commits_a = Column(Integer, nullable=False, default=0)
    total_commits_b = Column(Integer, nullable=False, default=0)
    first_coupled_date = Column(DateTime, nullable=True)
    last_coupled_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("repository_id", "file_path_a", "file_path_b", name="uq_coupling_unique"),
        Index("ix_coupling_repo_score", "repository_id", "coupling_score"),
        Index("ix_coupling_paths", "file_path_a", "file_path_b"),
        CheckConstraint("file_path_a < file_path_b", name="ck_coupling_path_order"),
    )

    repository = relationship("GitRepository", back_populates="couplings")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("git_repositories.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.queued)
    progress_percentage = Column(Integer, nullable=False, default=0)
    current_step = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    repository = relationship("GitRepository", back_populates="jobs")
