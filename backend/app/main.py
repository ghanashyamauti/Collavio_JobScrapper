import logging
import time
import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Tuple
from math import ceil
from datetime import datetime, timezone
import httpx

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, asc, or_, and_, distinct, nulls_last, case, text
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import get_db, init_db, DB_TYPE
from app.models import Job, JobSource, ScrapeRun
from app.schemas import (
    JobListResponse,
    JobOut,
    JobTrackUpdate,
    FiltersResponse,
    FacetItem,
    KpiMetrics,
    SyncStatusResponse,
    HealthResponse,
    ScrapeRunOut,
    SyncRequest,
    JobVerifyResponse,
    CompanyHarvestRequest,
    JobDetailResponse,
    LiveSearchResponse,
)
from app.normalizer import clean_html_description
from app.pipeline import run_ingestion, get_sync_telemetry, deactivate_expired_jobs, process_raw_jobs
from app.collectors.ats_collector import ATSCollector

logger = logging.getLogger("collavio")
logging.basicConfig(level=logging.INFO)

scheduler = BackgroundScheduler()


def scheduled_sync_job():
    logger.info("[Scheduler] Triggering scheduled job collection...")
    try:
        run_ingestion(mode="fast")
    except Exception as e:
        logger.error(f"[Scheduler] Error during scheduled sync: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    try:
        init_db()
        logger.info(f"[Startup] Database initialized with engine type: {DB_TYPE}")
    except Exception as e:
        logger.warning(f"[Startup] Database initialization skipped or deferred: {e}")

    # Start APScheduler
    if settings.SYNC_INTERVAL_HOURS > 0:
        try:
            scheduler.add_job(
                scheduled_sync_job,
                "interval",
                hours=settings.SYNC_INTERVAL_HOURS,
                id="collavio_scheduled_sync",
                replace_existing=True,
            )
            scheduler.start()
            logger.info(f"[Startup] APScheduler started: runs every {settings.SYNC_INTERVAL_HOURS} hours.")
        except Exception as e:
            logger.warning(f"[Startup] APScheduler startup skipped: {e}")

    # Automatically trigger background ingestion on startup in a separate daemon thread
    # so that new jobs and expired job deactivation happen immediately without manual clicks
    import threading
    threading.Thread(target=scheduled_sync_job, daemon=True, name="startup_auto_sync").start()
    logger.info("[Startup] Initiated background auto-sync thread.")

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Shutdown] APScheduler shut down.")


app = FastAPI(
    title="Collavio Jobs API",
    description="Collavio Jobs — Multi-Source Opportunity & Career Aggregator API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
allowed_origins = list(set([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    settings.FRONTEND_ORIGIN.rstrip("/"),
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check returning database type and scheduler state."""
    job_count = db.query(func.count(Job.id)).scalar() or 0
    return HealthResponse(
        status="ok",
        database=DB_TYPE,
        scheduler_running=scheduler.running,
        total_jobs=job_count,
    )


def get_experience_filter(exp_years: Optional[float]):
    """
    Returns SQL predicate for candidate experience matching:
    - 0 <= exp_years < 15: requires min_exp or max_exp to be populated,
      and coalesce(min_exp, 0) <= exp_years <= coalesce(max_exp, 30)
    - exp_years >= 15: min_exp >= 12 or max_exp >= 15
    """
    if exp_years is None or exp_years < 0:
        return None
    if 0 <= exp_years < 15:
        return and_(
            or_(Job.min_exp.is_not(None), Job.max_exp.is_not(None)),
            func.coalesce(Job.min_exp, 0) <= exp_years,
            func.coalesce(Job.max_exp, 30) >= exp_years,
        )
    elif exp_years >= 15:
        return or_(
            Job.min_exp >= 12,
            Job.max_exp >= 15,
        )
    return None


_stats_cache: Dict[str, Any] = {
    "data": None,
    "cached_at": 0.0,
}


def invalidate_stats_cache():
    global _stats_cache
    _stats_cache["data"] = None
    _stats_cache["cached_at"] = 0.0


@app.get("/api/stats", response_model=KpiMetrics)
def get_stats(db: Session = Depends(get_db)):
    """Dedicated cached KPI endpoint for StatsStrip (180s TTL, single-pass SQL)."""
    global _stats_cache
    now = time.time()
    if _stats_cache["data"] and (now - _stats_cache["cached_at"]) < 180:
        return _stats_cache["data"]

    is_postgres = (db.bind and db.bind.dialect.name == "postgresql")
    if is_postgres:
        kpi_sql = text("""
            SELECT 
                count(id) AS total_jobs,
                count(id) FILTER (WHERE is_active = true) AS active_jobs,
                count(id) FILTER (WHERE is_active = true AND country = 'India') AS india_jobs,
                count(id) FILTER (WHERE is_active = true AND is_remote = true) AS remote_jobs,
                count(id) FILTER (WHERE is_saved = true) AS saved_jobs,
                count(id) FILTER (WHERE application_status IN ('applied', 'interview', 'offer')) AS applied_jobs
            FROM jobs;
        """)
        try:
            row = db.execute(kpi_sql).mappings().one()
            total_jobs = row["total_jobs"] or 0
            active_jobs = row["active_jobs"] or 0
            india_jobs = row["india_jobs"] or 0
            remote_jobs = row["remote_jobs"] or 0
            saved_jobs = row["saved_jobs"] or 0
            applied_jobs = row["applied_jobs"] or 0
        except Exception:
            total_jobs = db.query(func.count(Job.id)).scalar() or 0
            active_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True).scalar() or 0
            india_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True, Job.country == "India").scalar() or 0
            remote_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True, Job.is_remote == True).scalar() or 0
            saved_jobs = db.query(func.count(Job.id)).filter(Job.is_saved == True).scalar() or 0
            applied_jobs = db.query(func.count(Job.id)).filter(Job.application_status.in_(["applied", "interview", "offer"])).scalar() or 0
    else:
        total_jobs = db.query(func.count(Job.id)).scalar() or 0
        active_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True).scalar() or 0
        india_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True, Job.country == "India").scalar() or 0
        remote_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True, Job.is_remote == True).scalar() or 0
        saved_jobs = db.query(func.count(Job.id)).filter(Job.is_saved == True).scalar() or 0
        applied_jobs = db.query(func.count(Job.id)).filter(Job.application_status.in_(["applied", "interview", "offer"])).scalar() or 0

    active_sources = db.query(func.count(distinct(JobSource.source_name))).scalar() or 0
    last_synced_at = db.query(func.max(ScrapeRun.finished_at)).scalar()

    metrics = KpiMetrics(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        india_jobs=india_jobs,
        remote_jobs=remote_jobs,
        saved_jobs=saved_jobs,
        applied_jobs=applied_jobs,
        active_sources=active_sources,
        last_synced_at=last_synced_at,
    )
    _stats_cache["data"] = metrics
    _stats_cache["cached_at"] = now
    return metrics


@app.get("/api/jobs", response_model=JobListResponse)
def get_jobs(
    q: Optional[str] = Query(None, description="Free text search query"),
    category: Optional[str] = Query(None, description="Job category"),
    location: Optional[str] = Query(None, description="Location or city filter"),
    country: Optional[str] = Query(None, description="Country filter (e.g. India, United States, Remote)"),
    india_only: Optional[bool] = Query(False, description="Filter for India roles only"),
    company: Optional[str] = Query(None, description="Company name filter"),
    source: Optional[str] = Query(None, description="Source platform name"),
    min_exp: Optional[float] = Query(None, description="Minimum experience required"),
    max_exp: Optional[float] = Query(None, description="Maximum experience required"),
    exp_years: Optional[float] = Query(None, description="Exact candidate experience in years"),
    remote_only: Optional[bool] = Query(False, description="Filter for remote jobs only"),
    active_only: Optional[bool] = Query(True, description="Filter for active non-expired jobs"),
    saved_only: Optional[bool] = Query(False, description="Filter for bookmarked jobs only"),
    application_status: Optional[str] = Query(None, description="Application tracking status"),
    job_type: Optional[str] = Query(None, description="Job type (Full-time, Contract, etc.)"),
    sort: Optional[str] = Query("newest", description="Sort option: newest, oldest, exp_asc, salary_desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Retrieves paginated, filtered jobs with multi-source listings and sub-second execution."""
    is_postgres = (db.bind and db.bind.dialect.name == "postgresql")
    query = select(Job)

    if active_only:
        query = query.where(Job.is_active == True)

    if q and q.strip():
        q_clean = q.strip()
        if is_postgres:
            query = query.where(
                or_(
                    text("jobs.search_vector @@ websearch_to_tsquery('english', :q_search)"),
                    Job.title.ilike(f"%{q_clean}%"),
                    Job.company.ilike(f"%{q_clean}%"),
                )
            ).params(q_search=q_clean)
        else:
            search_terms = q_clean.split()
            term_filters = []
            for term in search_terms:
                wildcard = f"%{term}%"
                term_filters.append(
                    or_(
                        Job.title.ilike(wildcard),
                        Job.company.ilike(wildcard),
                        Job.city.ilike(wildcard),
                        Job.location.ilike(wildcard),
                        Job.category.ilike(wildcard),
                    )
                )
            query = query.where(and_(*term_filters))

    if category:
        query = query.where(Job.category == category)

    if india_only:
        query = query.where(Job.country == "India")
    elif country:
        c_lower = country.strip().lower()
        if c_lower in ("india", "in"):
            query = query.where(Job.country == "India")
        elif "remote" in c_lower or "worldwide" in c_lower:
            query = query.where(
                or_(
                    Job.is_remote == True,
                    Job.country == "Remote / Worldwide",
                    Job.country.ilike("%remote%"),
                )
            )
        else:
            query = query.where(
                or_(
                    Job.country == country,
                    func.lower(Job.country) == c_lower,
                )
            )

    if location:
        loc_wild = f"%{location}%"
        query = query.where(or_(Job.city == location, Job.city.ilike(loc_wild), Job.location.ilike(loc_wild)))

    if company:
        query = query.where(or_(Job.company == company, Job.company.ilike(f"%{company}%")))

    if source:
        query = query.join(Job.sources).where(JobSource.source_name == source.lower())

    exp_filter = get_experience_filter(exp_years)
    if exp_filter is not None:
        query = query.where(exp_filter)
    elif min_exp is not None and max_exp is not None:
        query = query.where(
            or_(
                and_(Job.min_exp >= min_exp, Job.min_exp <= max_exp),
                and_(Job.max_exp >= min_exp, Job.max_exp <= max_exp),
                and_(Job.min_exp <= min_exp, Job.max_exp >= max_exp),
            )
        )
    elif min_exp is not None:
        query = query.where(or_(Job.min_exp >= min_exp, Job.max_exp >= min_exp))
    elif max_exp is not None:
        query = query.where(or_(Job.max_exp <= max_exp, and_(Job.min_exp <= max_exp, Job.max_exp == None)))

    if remote_only:
        query = query.where(Job.is_remote == True)

    if saved_only:
        query = query.where(Job.is_saved == True)

    if application_status and application_status != "all":
        query = query.where(Job.application_status == application_status)

    if job_type:
        query = query.where(Job.job_type.ilike(f"%{job_type}%"))

    # Sorting
    if sort == "oldest":
        query = query.order_by(nulls_last(asc(Job.posted_at)), asc(Job.id))
    elif sort == "exp_asc":
        query = query.order_by(nulls_last(asc(Job.min_exp)), nulls_last(desc(Job.posted_at)))
    elif sort == "salary_desc":
        query = query.order_by(nulls_last(desc(Job.salary_max)), nulls_last(desc(Job.posted_at)))
    elif q and q.strip():
        full_phrase = f"%{q.strip()}%"
        q_words = q.strip().split()
        relevance_rank = case(
            (Job.title.ilike(full_phrase), 1),
            (and_(*[Job.title.ilike(f"%{w}%") for w in q_words]), 2),
            (Job.company.ilike(full_phrase), 3),
            (Job.city.ilike(full_phrase), 4),
            else_=5,
        )
        query = query.order_by(relevance_rank, nulls_last(desc(Job.posted_at)), desc(Job.id))
    else:
        query = query.order_by(nulls_last(desc(Job.posted_at)), desc(Job.id))

    offset = (page - 1) * page_size
    # Single-round-trip: get jobs + total count in 1 query via COUNT(*) OVER()
    paged_stmt = query.add_columns(func.count().over().label("total_count")).limit(page_size).offset(offset)
    rows = db.execute(paged_stmt).all()

    if rows:
        jobs = [r[0] for r in rows]
        total = rows[0][1]
    else:
        if offset > 0:
            count_sub = (
                query.with_only_columns(func.count(distinct(Job.id))).order_by(None)
                if source
                else query.with_only_columns(func.count(Job.id)).order_by(None)
            )
            total = db.execute(count_sub).scalar() or 0
        else:
            total = 0
        jobs = []

    total_pages = ceil(total / page_size) if total > 0 else 1

    return JobListResponse(
        jobs=[JobOut.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


_live_search_cache: Dict[str, Any] = {}


@app.get("/api/jobs/live-search", response_model=LiveSearchResponse)
def live_search_jobs(
    q: Optional[str] = Query(None, description="Job title, skills, or query"),
    location: Optional[str] = Query(None, description="City, state, or location"),
    country: Optional[str] = Query("India", description="Country for search"),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Real-time live search fallback across Naukri, LinkedIn, Indeed, Glassdoor via JobSpy.
    Caches results in-memory for 10 minutes to protect rate limits while delivering
    instant fresh results for any city or role in the world.
    """
    clean_q = (q or "").strip()
    clean_loc = (location or "").strip()
    clean_country = (country or "India").strip()

    cache_key = f"{clean_q.lower()}|{clean_loc.lower()}|{clean_country.lower()}"
    now = datetime.now(timezone.utc)

    if cache_key in _live_search_cache:
        cached_time, cached_items = _live_search_cache[cache_key]
        if (now - cached_time).total_seconds() < 600:
            return LiveSearchResponse(
                query=clean_q,
                location=clean_loc,
                country=clean_country,
                cached=True,
                total_found=len(cached_items),
                jobs=cached_items[:limit],
            )

    try:
        from app.collectors.jobspy_collector import JobSpyCollector
        collector = JobSpyCollector(
            queries=[clean_q] if clean_q else ["Software Engineer"],
            locations=[clean_loc] if clean_loc else ["Remote"],
            country_indeed=clean_country,
            results_per_query=limit,
        )
        raw_jobs = collector.collect()
    except Exception as e:
        logger.warning(f"[LiveSearch] JobSpy collector failed: {e}")
        raw_jobs = []

    if not raw_jobs:
        return LiveSearchResponse(
            query=clean_q,
            location=clean_loc,
            country=clean_country,
            cached=False,
            total_found=0,
            jobs=[],
        )

    try:
        process_raw_jobs(db, raw_jobs, "live_search")
    except Exception as e:
        logger.warning(f"[LiveSearch] Error persisting live jobs: {e}")

    from app.normalizer import generate_fingerprint, normalize_company, normalize_title
    fps = [
        generate_fingerprint(normalize_company(rj.company), normalize_title(rj.title), rj.location)
        for rj in raw_jobs
    ]
    db_jobs = (
        db.execute(select(Job).where(Job.fingerprint_hash.in_(fps)))
        .scalars()
        .all()
    )

    out_jobs: List[JobOut] = []
    for j in db_jobs:
        job_out = JobOut.model_validate(j)
        job_out.is_live_scraped = True
        out_jobs.append(job_out)

    _live_search_cache[cache_key] = (now, out_jobs)

    return LiveSearchResponse(
        query=clean_q,
        location=clean_loc,
        country=clean_country,
        cached=False,
        total_found=len(out_jobs),
        jobs=out_jobs[:limit],
    )


@app.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Fetches single job details by ID."""
    job = db.execute(select(Job).where(Job.id == job_id)).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


@app.get("/api/jobs/{job_id}/detail", response_model=JobDetailResponse)
async def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """
    On-demand live description fetcher.
    If job.description is already populated, returns it immediately.
    If NULL, fetches live from Greenhouse API, Workday CXS, or employer URL.
    If employer returns 404/410, marks job as inactive (expired) and returns status='expired'.
    """
    job = db.execute(select(Job).where(Job.id == job_id)).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    primary_source = job.sources[0] if job.sources else None
    apply_url = primary_source.apply_url if primary_source else None
    external_id = primary_source.external_id if primary_source else None
    source_name = (primary_source.source_name if primary_source else "").lower()

    if job.description:
        # Check freshness: if updated_at is older than 24 hours and job is active, perform lightweight async check
        check_time = job.updated_at or job.created_at
        is_stale = False
        if check_time:
            now_utc = datetime.now(timezone.utc)
            if check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=timezone.utc)
            if (now_utc - check_time).total_seconds() > 86400:
                is_stale = True

        if is_stale and apply_url and job.is_active:
            try:
                async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                    resp = await client.head(
                        apply_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    )
                    if resp.status_code in (404, 410):
                        job.is_active = False
                        job.updated_at = datetime.now(timezone.utc)
                        db.commit()
                        return JobDetailResponse(
                            id=job.id,
                            description=job.description,
                            is_active=False,
                            status="expired",
                            apply_url=apply_url,
                        )
                    if resp.status_code == 405:
                        resp = await client.get(
                            apply_url,
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                        )
                        if resp.status_code in (404, 410):
                            job.is_active = False
                            job.updated_at = datetime.now(timezone.utc)
                            db.commit()
                            return JobDetailResponse(
                                id=job.id,
                                description=job.description,
                                is_active=False,
                                status="expired",
                                apply_url=apply_url,
                            )
                        text_sample = resp.text[:5000].lower()
                        if any(marker in text_sample for marker in [
                            "this job is no longer available",
                            "position has been filled",
                            "job posting has expired",
                            "job is no longer active",
                            "this posting has been closed",
                        ]):
                            job.is_active = False
                            job.updated_at = datetime.now(timezone.utc)
                            db.commit()
                            return JobDetailResponse(
                                id=job.id,
                                description=job.description,
                                is_active=False,
                                status="expired",
                                apply_url=apply_url,
                            )
            except Exception as e:
                logger.debug(f"24h freshness check skipped for job {job_id}: {e}")

        return JobDetailResponse(
            id=job.id,
            description=job.description,
            is_active=job.is_active,
            status="cached",
            apply_url=apply_url,
        )

    fetched_html = None
    is_expired = False

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            # 1. Greenhouse Detail API
            if "greenhouse" in source_name or "greenhouse.io" in (apply_url or ""):
                import re
                slug = job.normalized_company.replace(" ", "").lower()
                gh_id = external_id
                if gh_id and gh_id.startswith("gh_"):
                    gh_id = gh_id[3:]
                if apply_url:
                    match_url = re.search(r"greenhouse\.io/(?:embed/job_board/)?([^/]+)/jobs/(\d+)", apply_url)
                    if match_url:
                        slug = match_url.group(1)
                        gh_id = match_url.group(2)
                    elif not gh_id:
                        match = re.search(r"/jobs/(\d+)", apply_url)
                        if match:
                            gh_id = match.group(1)
                if gh_id:
                    detail_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{gh_id}"
                    resp = await client.get(detail_url)
                    if resp.status_code in (404, 410):
                        is_expired = True
                    elif resp.status_code == 200:
                        gh_data = resp.json()
                        fetched_html = gh_data.get("content")

            # 2. Workday Detail CXS Endpoint
            elif "workday" in source_name or "myworkdayjobs.com" in (apply_url or ""):
                if apply_url:
                    resp = await client.get(apply_url)
                    if resp.status_code in (404, 410):
                        is_expired = True
                    elif resp.status_code == 200:
                        try:
                            w_data = resp.json()
                            fetched_html = w_data.get("jobPostingInfo", {}).get("jobDescription")
                        except Exception:
                            fetched_html = resp.text

            # 3. Generic Apply URL fetch fallback
            elif apply_url:
                resp = await client.get(
                    apply_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                if resp.status_code in (404, 410):
                    is_expired = True
                elif resp.status_code == 200:
                    fetched_html = resp.text

        except Exception as fetch_err:
            logger.warning(f"Failed to fetch live description for job {job_id}: {fetch_err}")

    if is_expired:
        job.is_active = False
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        return JobDetailResponse(
            id=job.id,
            description=None,
            is_active=False,
            status="expired",
            apply_url=apply_url,
        )

    if fetched_html:
        clean_desc = clean_html_description(fetched_html)
        if clean_desc:
            job.description = clean_desc
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
            return JobDetailResponse(
                id=job.id,
                description=clean_desc,
                is_active=job.is_active,
                status="live_fetched",
                apply_url=apply_url,
            )

    return JobDetailResponse(
        id=job.id,
        description=job.description,
        is_active=job.is_active,
        status="unavailable",
        apply_url=apply_url,
    )


@app.patch("/api/jobs/{job_id}/track", response_model=JobOut)
def track_job(job_id: int, payload: JobTrackUpdate, db: Session = Depends(get_db)):
    """Updates job bookmark status, application tracking status, and personal notes."""
    job = db.execute(select(Job).where(Job.id == job_id)).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if payload.is_saved is not None:
        job.is_saved = payload.is_saved

    if payload.application_status is not None:
        status_val = payload.application_status.strip().lower()
        valid_statuses = {"none", "saved", "applied", "interview", "offer", "rejected"}
        if status_val not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid application status '{status_val}'")
        job.application_status = status_val
        # Setting any non-none status automatically marks is_saved=True
        if status_val != "none":
            job.is_saved = True

    if payload.notes is not None:
        job.notes = payload.notes

    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    invalidate_filters_cache()
    return JobOut.model_validate(job)


def build_cte_facets_query(
    q: Optional[str] = None,
    exp_years: Optional[float] = None,
    remote_only: Optional[bool] = False,
    active_only: Optional[bool] = True,
    india_only: Optional[bool] = False,
    country: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    company: Optional[str] = None,
    source: Optional[str] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Builds a single-round-trip CTE SQL query that computes all 5 cross-faceted scopes."""
    params: Dict[str, Any] = {}
    base_wheres = []
    if active_only:
        base_wheres.append("j.is_active = true")

    if india_only:
        base_wheres.append("j.country = 'India'")

    if remote_only:
        base_wheres.append("j.is_remote = true")

    if exp_years is not None and exp_years >= 0:
        if exp_years >= 15:
            base_wheres.append("(j.min_exp >= 12 OR j.max_exp >= 15)")
        else:
            base_wheres.append("(j.min_exp IS NOT NULL OR j.max_exp IS NOT NULL) AND coalesce(j.min_exp, 0) <= :exp_years AND coalesce(j.max_exp, 30) >= :exp_years")
            params["exp_years"] = float(exp_years)

    if q and q.strip():
        base_wheres.append("j.search_vector @@ websearch_to_tsquery('english', :q_search)")
        params["q_search"] = q.strip()

    base_where_sql = " AND ".join(base_wheres) if base_wheres else "1=1"

    cond_country = None
    if country and not india_only:
        c_low = country.strip().lower()
        if c_low in ("india", "in"):
            cond_country = "country = 'India'"
        elif "remote" in c_low or "worldwide" in c_low:
            cond_country = "(is_remote = true OR country = 'Remote / Worldwide')"
        else:
            cond_country = "(country = :country OR lower(country) = :country_low)"
            params["country"] = country
            params["country_low"] = c_low

    cond_city = None
    if city and city.strip():
        cond_city = "(city = :city OR city ILIKE :city_pattern)"
        params["city"] = city.strip()
        params["city_pattern"] = f"%{city.strip()}%"

    cond_cat = None
    if category and category.strip():
        cond_cat = "category = :category"
        params["category"] = category.strip()

    cond_comp = None
    if company and company.strip():
        cond_comp = "(company = :company OR company ILIKE :comp_pattern)"
        params["company"] = company.strip()
        params["comp_pattern"] = f"%{company.strip()}%"

    cond_source = None
    if source and source.strip():
        cond_source = "js.source_name = :src_filter"
        params["src_filter"] = source.strip().lower()

    # Countries facet (excludes country and city)
    f_countries = [c for c in [cond_cat, cond_comp] if c]
    f_countries_sql = (" AND " + " AND ".join(f_countries)) if f_countries else ""

    # Cities facet (excludes city)
    f_cities = [c for c in [cond_country, cond_cat, cond_comp] if c]
    f_cities_sql = (" AND " + " AND ".join(f_cities)) if f_cities else ""

    # Categories facet (excludes category)
    f_categories = [c for c in [cond_country, cond_city, cond_comp] if c]
    f_categories_sql = (" AND " + " AND ".join(f_categories)) if f_categories else ""

    # Companies facet (excludes company)
    f_companies = [c for c in [cond_country, cond_city, cond_cat] if c]
    f_companies_sql = (" AND " + " AND ".join(f_companies)) if f_companies else ""

    # Sources facet (excludes source)
    f_sources = [c for c in [cond_country, cond_city, cond_cat, cond_comp] if c]
    f_sources_sql = (" AND " + " AND ".join(f_sources)) if f_sources else ""

    sql = f"""
    WITH
    base_jobs AS (
        SELECT j.id, j.country, j.city, j.category, j.company, j.is_remote
        FROM jobs j
        WHERE {base_where_sql}
    ),
    countries_cte AS (
        SELECT country AS name, COUNT(*) AS count
        FROM base_jobs
        WHERE country IS NOT NULL {f_countries_sql}
        GROUP BY country
        HAVING COUNT(*) > 0
        ORDER BY count DESC
    ),
    cities_cte AS (
        SELECT city AS name, COUNT(*) AS count
        FROM base_jobs
        WHERE city IS NOT NULL {f_cities_sql}
        GROUP BY city
        HAVING COUNT(*) > 0
        ORDER BY count DESC
        LIMIT 200
    ),
    categories_cte AS (
        SELECT category AS name, COUNT(*) AS count
        FROM base_jobs
        WHERE category IS NOT NULL {f_categories_sql}
        GROUP BY category
        HAVING COUNT(*) > 0
        ORDER BY count DESC
    ),
    companies_cte AS (
        SELECT company AS name, COUNT(*) AS count
        FROM base_jobs
        WHERE company IS NOT NULL {f_companies_sql}
        GROUP BY company
        HAVING COUNT(*) > 0
        ORDER BY count DESC
        LIMIT 200
    ),
    sources_cte AS (
        SELECT js.source_name AS name, COUNT(DISTINCT js.job_id) AS count
        FROM job_sources js
        JOIN base_jobs bj ON bj.id = js.job_id
        WHERE 1=1 {f_sources_sql}
        GROUP BY js.source_name
        HAVING COUNT(DISTINCT js.job_id) > 0
        ORDER BY count DESC
    )
    SELECT json_build_object(
        'countries', (SELECT coalesce(json_agg(countries_cte), '[]'::json) FROM countries_cte),
        'cities', (SELECT coalesce(json_agg(cities_cte), '[]'::json) FROM cities_cte),
        'categories', (SELECT coalesce(json_agg(categories_cte), '[]'::json) FROM categories_cte),
        'companies', (SELECT coalesce(json_agg(companies_cte), '[]'::json) FROM companies_cte),
        'sources', (SELECT coalesce(json_agg(sources_cte), '[]'::json) FROM sources_cte)
    ) AS facets;
    """
    return text(sql), params


_filters_lru_cache: Dict[str, Dict[str, Any]] = {}


def invalidate_filters_cache():
    global _filters_lru_cache
    _filters_lru_cache.clear()
    invalidate_stats_cache()


@app.get("/api/filters", response_model=FiltersResponse)
def get_filters(
    q: Optional[str] = Query(None, description="Search query filter"),
    country: Optional[str] = Query(None, description="Country filter"),
    india_only: Optional[bool] = Query(False, description="Filter for India roles only"),
    location: Optional[str] = Query(None, description="City filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    company: Optional[str] = Query(None, description="Company filter"),
    source: Optional[str] = Query(None, description="Source filter"),
    exp_years: Optional[float] = Query(None, description="Exact candidate experience in years"),
    remote_only: Optional[bool] = Query(False, description="Filter for remote jobs only"),
    active_only: Optional[bool] = Query(True, description="Filter for active non-expired jobs"),
    db: Session = Depends(get_db),
):
    """Universal Dynamic Cross-Faceted endpoint. All 5 facets dynamically scoped in ONE SQL trip."""
    cache_key = f"{q or ''}|{country or ''}|{india_only}|{location or ''}|{category or ''}|{company or ''}|{source or ''}|{exp_years}|{remote_only}|{active_only}"
    now = time.time()

    if cache_key in _filters_lru_cache:
        cached_entry = _filters_lru_cache[cache_key]
        if (now - cached_entry["cached_at"]) < 120:
            return cached_entry["response"]

    kpis = get_stats(db)
    is_postgres = (db.bind and db.bind.dialect.name == "postgresql")

    if is_postgres:
        sql, params = build_cte_facets_query(
            q=q,
            exp_years=exp_years,
            remote_only=remote_only,
            active_only=active_only,
            india_only=india_only,
            country=country,
            city=location,
            category=category,
            company=company,
            source=source,
        )
        res_json = db.execute(sql, params).scalar()
        facets_dict = json.loads(res_json) if isinstance(res_json, str) else (res_json or {})

        countries = [FacetItem(name=item["name"], count=item["count"]) for item in facets_dict.get("countries", []) if item.get("name") and item.get("count", 0) > 0]
        cities = [FacetItem(name=item["name"], count=item["count"]) for item in facets_dict.get("cities", []) if item.get("name") and item.get("count", 0) > 0]
        categories = [FacetItem(name=item["name"], count=item["count"]) for item in facets_dict.get("categories", []) if item.get("name") and item.get("count", 0) > 0]
        companies = [FacetItem(name=item["name"], count=item["count"]) for item in facets_dict.get("companies", []) if item.get("name") and item.get("count", 0) > 0]
        sources = [FacetItem(name=item["name"], count=item["count"]) for item in facets_dict.get("sources", []) if item.get("name") and item.get("count", 0) > 0]
    else:
        # SQLite fallback for test environment
        exp_cond = get_experience_filter(exp_years)

        # Base filter builder for SQLite
        def build_sqlite_query(exclude_facet: str):
            q_stmt = select(Job)
            if active_only:
                q_stmt = q_stmt.where(Job.is_active == True)
            if exp_cond is not None:
                q_stmt = q_stmt.where(exp_cond)
            if remote_only:
                q_stmt = q_stmt.where(Job.is_remote == True)
            if india_only:
                q_stmt = q_stmt.where(Job.country == "India")

            if exclude_facet != "country" and country and not india_only:
                c_low = country.strip().lower()
                if c_low in ("india", "in"):
                    q_stmt = q_stmt.where(Job.country == "India")
                elif "remote" in c_low or "worldwide" in c_low:
                    q_stmt = q_stmt.where(or_(Job.is_remote == True, Job.country == "Remote / Worldwide"))
                else:
                    q_stmt = q_stmt.where(or_(Job.country == country, func.lower(Job.country) == c_low))

            if exclude_facet != "city" and location:
                q_stmt = q_stmt.where(or_(Job.city == location, Job.city.ilike(f"%{location}%")))

            if exclude_facet != "category" and category:
                q_stmt = q_stmt.where(Job.category == category)

            if exclude_facet != "company" and company:
                q_stmt = q_stmt.where(or_(Job.company == company, Job.company.ilike(f"%{company}%")))

            if exclude_facet != "source" and source:
                q_stmt = q_stmt.join(Job.sources).where(JobSource.source_name == source.lower())

            return q_stmt

        # Countries
        cq = build_sqlite_query("country")
        country_rows = db.execute(
            cq.with_only_columns(Job.country, func.count(Job.id))
            .where(Job.country != None)
            .group_by(Job.country)
            .having(func.count(Job.id) > 0)
            .order_by(desc(func.count(Job.id)))
        ).all()
        countries = [FacetItem(name=r[0], count=r[1]) for r in country_rows if r[0] and r[1] > 0]

        # Cities
        city_q = build_sqlite_query("city")
        city_rows = db.execute(
            city_q.with_only_columns(Job.city, func.count(Job.id))
            .where(Job.city != None)
            .group_by(Job.city)
            .having(func.count(Job.id) > 0)
            .order_by(desc(func.count(Job.id)))
            .limit(200)
        ).all()
        cities = [FacetItem(name=r[0], count=r[1]) for r in city_rows if r[0] and r[1] > 0]

        # Categories
        cat_q = build_sqlite_query("category")
        cat_rows = db.execute(
            cat_q.with_only_columns(Job.category, func.count(Job.id))
            .where(Job.category != None)
            .group_by(Job.category)
            .having(func.count(Job.id) > 0)
            .order_by(desc(func.count(Job.id)))
        ).all()
        categories = [FacetItem(name=r[0], count=r[1]) for r in cat_rows if r[0] and r[1] > 0]

        # Companies
        comp_q = build_sqlite_query("company")
        comp_rows = db.execute(
            comp_q.with_only_columns(Job.company, func.count(Job.id))
            .where(Job.company != None)
            .group_by(Job.company)
            .having(func.count(Job.id) > 0)
            .order_by(desc(func.count(Job.id)))
            .limit(200)
        ).all()
        companies = [FacetItem(name=r[0], count=r[1]) for r in comp_rows if r[0] and r[1] > 0]

        # Sources
        src_q = build_sqlite_query("source")
        src_rows = db.execute(
            src_q.join(Job.sources)
            .with_only_columns(JobSource.source_name, func.count(distinct(Job.id)))
            .group_by(JobSource.source_name)
            .having(func.count(distinct(Job.id)) > 0)
            .order_by(desc(func.count(distinct(Job.id))))
        ).all()
        sources = [FacetItem(name=r[0], count=r[1]) for r in src_rows if r[0] and r[1] > 0]

    job_types = [FacetItem(name="Full-time", count=kpis.active_jobs)]

    response = FiltersResponse(
        categories=categories,
        cities=cities,
        countries=countries,
        companies=companies,
        sources=sources,
        job_types=job_types,
        kpis=kpis,
    )

    if len(_filters_lru_cache) >= 256:
        _filters_lru_cache.clear()
    _filters_lru_cache[cache_key] = {"response": response, "cached_at": now}
    return response


@app.post("/api/jobs/{job_id}/verify", response_model=JobVerifyResponse)
def verify_job_liveness(job_id: int, db: Session = Depends(get_db)):
    """Probes the live career URL. If 404, 410, or expired, automatically deactivates the job."""
    job = db.execute(select(Job).where(Job.id == job_id)).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    primary_url = job.sources[0].apply_url if job.sources else None
    if not primary_url:
        return JobVerifyResponse(
            job_id=job_id,
            is_active=job.is_active,
            message="No external application URL recorded for verification",
        )

    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.head(primary_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if resp.status_code in (405, 403):
                resp = client.get(primary_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

            status_code = resp.status_code
            if status_code in (404, 410):
                job.is_active = False
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
                return JobVerifyResponse(
                    job_id=job_id,
                    is_active=False,
                    status_code=status_code,
                    message="Position closed or page removed (HTTP 404/410). Job automatically marked expired.",
                )
            elif status_code < 400:
                return JobVerifyResponse(
                    job_id=job_id,
                    is_active=True,
                    status_code=status_code,
                    message="Position verified live and actively accepting applications.",
                )
            else:
                return JobVerifyResponse(
                    job_id=job_id,
                    is_active=job.is_active,
                    status_code=status_code,
                    message=f"Received HTTP {status_code} from provider.",
                )
    except Exception as e:
        return JobVerifyResponse(
            job_id=job_id,
            is_active=job.is_active,
            message=f"Network probe timed out: {e}",
        )


@app.post("/api/jobs/{job_id}/expire", response_model=JobOut)
def expire_job(job_id: int, db: Session = Depends(get_db)):
    """Manually marks a job as expired/closed."""
    job = db.execute(select(Job).where(Job.id == job_id)).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_active = False
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    invalidate_filters_cache()
    return JobOut.model_validate(job)


@app.post("/api/jobs/cleanup-expired")
def cleanup_expired_jobs(days: int = Query(45, ge=1), db: Session = Depends(get_db)):
    """Deactivates jobs older than the specified threshold."""
    count = deactivate_expired_jobs(db, max_age_days=days)
    return {
        "cleaned_count": count,
        "message": f"Deactivated {count} expired/stale postings older than {days} days.",
    }


@app.get("/api/sync/status", response_model=SyncStatusResponse)
def get_sync_status(db: Session = Depends(get_db)):
    """Returns telemetry of running collector and last 15 scrape runs."""
    state = get_sync_telemetry()
    recent_runs = (
        db.execute(
            select(ScrapeRun).order_by(desc(ScrapeRun.id)).limit(15)
        )
        .scalars()
        .all()
    )

    return SyncStatusResponse(
        is_running=state.get("is_running", False),
        active_collector=state.get("active_collector"),
        recent_runs=[ScrapeRunOut.model_validate(r) for r in recent_runs],
    )


@app.post("/api/sync")
def trigger_sync(
    background_tasks: BackgroundTasks,
    mode: str = Query("fast", description="Ingestion mode: 'fast' (~10-15s) or 'full' (includes JobSpy)"),
    payload: Optional[SyncRequest] = None,
):
    """
    Triggers background data collection with duplicate execution protection.
    Accepts dynamic queries and locations for real-time live harvesting.
    """
    state = get_sync_telemetry()
    if state.get("is_running"):
        return {"status": "busy", "message": "An ingestion run is already in progress"}

    sync_mode = payload.mode if payload and payload.mode else mode
    queries = payload.queries if payload else None
    locations = payload.locations if payload else None
    country = payload.country if payload and payload.country else "India"
    sources = payload.sources if payload else None

    background_tasks.add_task(
        run_ingestion,
        sources=sources,
        mode=sync_mode,
        queries=queries,
        locations=locations,
        country=country,
    )
    return {
        "status": "started",
        "mode": sync_mode,
        "queries": queries,
        "locations": locations,
        "country": country,
        "sources": sources,
        "message": f"Background job ingestion triggered in '{sync_mode}' mode.",
    }


@app.post("/api/harvest/company")
def harvest_company(payload: CompanyHarvestRequest, db: Session = Depends(get_db)):
    """Dynamically probes and ingests jobs for ANY company across Greenhouse, Lever, and Ashby."""
    comp_clean = payload.company.strip()
    if not comp_clean:
        raise HTTPException(status_code=400, detail="Company identifier or name is required.")

    collector = ATSCollector()
    raw_jobs = collector.harvest_single_company(comp_clean)
    if not raw_jobs:
        return {
            "status": "not_found",
            "company": comp_clean,
            "jobs_found": 0,
            "message": f"No active public ATS board found for '{comp_clean}'. You can also use Live Harvest to search any city/role via JobSpy.",
        }

    found, new_cnt, merged_cnt = process_raw_jobs(db, raw_jobs, f"dynamic_{comp_clean.lower()}")
    return {
        "status": "success",
        "company": comp_clean,
        "jobs_found": found,
        "new_jobs": new_cnt,
        "duplicates_merged": merged_cnt,
        "message": f"Successfully ingested {new_cnt} new jobs ({found} total found) from {comp_clean}.",
    }
