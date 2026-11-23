from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class JobSourceOut(BaseModel):
    id: int
    job_id: int
    source_name: str
    external_id: Optional[str] = None
    apply_url: str
    scraped_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobOut(BaseModel):
    id: int
    fingerprint_hash: str
    title: str
    normalized_title: str
    company: str
    normalized_company: str
    category: str
    location: Optional[str] = None
    city: Optional[str] = None
    is_remote: bool
    min_exp: Optional[float] = None
    max_exp: Optional[float] = None
    job_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    is_saved: bool
    application_status: str
    notes: Optional[str] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sources: List[JobSourceOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class JobTrackUpdate(BaseModel):
    is_saved: Optional[bool] = None
    application_status: Optional[str] = None
    notes: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: List[JobOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class FacetItem(BaseModel):
    name: str
    count: int


class KpiMetrics(BaseModel):
    total_jobs: int
    remote_jobs: int
    saved_jobs: int
    applied_jobs: int
    active_sources: int
    last_synced_at: Optional[datetime] = None


class FiltersResponse(BaseModel):
    categories: List[FacetItem]
    cities: List[FacetItem]
    companies: List[FacetItem]
    sources: List[FacetItem]
    job_types: List[FacetItem]
    kpis: KpiMetrics


class ScrapeRunOut(BaseModel):
    id: int
    source: str
    jobs_found: int
    new_jobs: int
    duplicates_merged: int
    status: str
    error_message: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SyncStatusResponse(BaseModel):
    is_running: bool
    active_collector: Optional[str] = None
    recent_runs: List[ScrapeRunOut] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    database: str
    scheduler_running: bool
    total_jobs: int
