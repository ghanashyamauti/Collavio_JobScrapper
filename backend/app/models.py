from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fingerprint_hash = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    normalized_title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    normalized_company = Column(String(255), index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    location = Column(String(255), nullable=True)
    city = Column(String(100), index=True, nullable=True)
    country = Column(String(100), index=True, nullable=True)
    is_remote = Column(Boolean, default=False, index=True, nullable=False)
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    min_exp = Column(Float, nullable=True)
    max_exp = Column(Float, nullable=True)
    job_type = Column(String(50), nullable=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    description = Column(Text, nullable=True)
    is_saved = Column(Boolean, default=False, index=True, nullable=False)
    application_status = Column(String(20), default="none", index=True, nullable=False)
    notes = Column(Text, nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sources = relationship(
        "JobSource",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class JobSource(Base):
    __tablename__ = "job_sources"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name = Column(String(100), nullable=False, index=True)
    external_id = Column(String(255), nullable=True)
    apply_url = Column(Text, nullable=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("job_id", "source_name", name="uq_job_source"),
    )

    job = relationship("Job", back_populates="sources")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source = Column(String(100), nullable=False, index=True)
    jobs_found = Column(Integer, default=0, nullable=False)
    new_jobs = Column(Integer, default=0, nullable=False)
    duplicates_merged = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="running", nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
