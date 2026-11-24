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
    country: Optional[str] = None
    is_remote: bool
    is_active: bool = True
    expires_at: Optional[datetime] = None
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
    is_live_scraped: bool = False
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sources: List[JobSourceOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class JobTrackUpdate(BaseModel):
    is_saved: Optional[bool] = None
    application_status: Optional[str] = None
    notes: Optional[str] = None


class JobDetailResponse(BaseModel):
    id: int
    description: Optional[str] = None
    is_active: bool = True
    status: str = "cached"  # cached, live_fetched, expired, unavailable
    apply_url: Optional[str] = None


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
    active_jobs: int = 0
    india_jobs: int = 0
    remote_jobs: int
    saved_jobs: int
    applied_jobs: int
    active_sources: int
    last_synced_at: Optional[datetime] = None


StatsResponse = KpiMetrics


class FiltersResponse(BaseModel):
    categories: List[FacetItem]
    cities: List[FacetItem]
    countries: List[FacetItem] = Field(default_factory=list)
    companies: List[FacetItem]
    sources: List[FacetItem]
    job_types: List[FacetItem]
    kpis: KpiMetrics


class SyncRequest(BaseModel):
    mode: str = "fast"
    sources: Optional[List[str]] = None
    queries: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    country: Optional[str] = "India"


class JobVerifyResponse(BaseModel):
    job_id: int
    is_active: bool
    status_code: Optional[int] = None
    message: str


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


class CompanyHarvestRequest(BaseModel):
    company: str


class LiveSearchResponse(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    cached: bool = False
    total_found: int
    jobs: List[JobOut] = Field(default_factory=list)

