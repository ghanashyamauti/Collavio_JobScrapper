import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from math import ceil
from datetime import datetime, timezone
import httpx

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, asc, or_, and_, distinct, nulls_last
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
)
from app.pipeline import run_ingestion, get_sync_telemetry, deactivate_expired_jobs, process_raw_jobs
from app.collectors.ats_collector import ATSCollector

logger = logging.getLogger("jobpulse")
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
                id="jobpulse_scheduled_sync",
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
    """Retrieves paginated, filtered jobs with multi-source listings."""
    query = select(Job)

    # Active jobs only by default (hides expired/removed postings)
    if active_only:
        query = query.where(Job.is_active == True)

    # Free text search across title, company, description
    if q and q.strip():
        search_terms = q.strip().split()
        for term in search_terms:
            wildcard = f"%{term}%"
            query = query.where(
                or_(
                    Job.title.ilike(wildcard),
                    Job.company.ilike(wildcard),
                    Job.location.ilike(wildcard),
                    Job.description.ilike(wildcard),
                )
            )

    if category:
        query = query.where(Job.category == category)

    if india_only:
        # Match jobs detected as India or with India / Bengaluru in location or city
        query = query.where(
            or_(
                Job.country == "India",
                Job.location.ilike("%india%"),
                Job.city.ilike("%bengaluru%"),
                Job.city.ilike("%bangalore%"),
            )
        )
    elif country:
        c_lower = country.strip().lower()
        if c_lower in ("india", "in"):
            query = query.where(
                or_(
                    Job.country == "India",
                    Job.location.ilike("%india%"),
                    Job.city.ilike("%bengaluru%"),
                )
            )
        elif "remote" in c_lower or "worldwide" in c_lower:
            query = query.where(
                or_(
                    Job.is_remote == True,
                    Job.country == "Remote / Worldwide",
                    Job.country.ilike("%remote%"),
                    Job.location.ilike("%remote%"),
                )
            )
        else:
            query = query.where(
                or_(
                    Job.country == country,
                    Job.country.ilike(f"%{country}%"),
                    Job.location.ilike(f"%{country}%"),
                )
            )

    if location:
        loc_wild = f"%{location}%"
        query = query.where(or_(Job.city.ilike(loc_wild), Job.location.ilike(loc_wild)))

    if company:
        query = query.where(Job.company.ilike(f"%{company}%"))

    if source:
        query = query.join(Job.sources).where(JobSource.source_name == source.lower())

    if min_exp is not None:
        query = query.where(or_(Job.min_exp == None, Job.min_exp <= min_exp))

    if max_exp is not None:
        query = query.where(or_(Job.max_exp == None, Job.max_exp <= max_exp))

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
    else:  # "newest"
        query = query.order_by(nulls_last(desc(Job.posted_at)), desc(Job.id))

    # Count total
    count_subquery = query.with_only_columns(func.count(distinct(Job.id))).order_by(None)
    total = db.execute(count_subquery).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    paged_query = query.distinct().offset(offset).limit(page_size)
    jobs = db.execute(paged_query).scalars().all()

    total_pages = ceil(total / page_size) if total > 0 else 1

    return JobListResponse(
        jobs=[JobOut.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Fetches single job details by ID."""
    job = db.execute(select(Job).where(Job.id == job_id)).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


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
    return JobOut.model_validate(job)


@app.get("/api/filters", response_model=FiltersResponse)
def get_filters(
    country: Optional[str] = Query(None, description="Filter facets by selected country"),
    db: Session = Depends(get_db)
):
    """Computes dynamic facet counts and top-level KPIs for dashboard sidebar and ribbon."""
    # Countries
    country_rows = db.execute(
        select(Job.country, func.count(Job.id))
        .where(Job.is_active == True, Job.country != None)
        .group_by(Job.country)
        .order_by(desc(func.count(Job.id)))
    ).all()
    countries = [FacetItem(name=r[0], count=r[1]) for r in country_rows if r[0]]

    # Categories
    cat_rows = db.execute(
        select(Job.category, func.count(Job.id))
        .where(Job.is_active == True)
        .group_by(Job.category)
        .order_by(desc(func.count(Job.id)))
    ).all()
    categories = [FacetItem(name=r[0], count=r[1]) for r in cat_rows if r[0]]

    # Cities (Filter by country if selected, so only that country's cities appear)
    city_query = select(Job.city, func.count(Job.id)).where(Job.is_active == True, Job.city != None)
    if country:
        c_lower = country.strip().lower()
        if c_lower in ("india", "in"):
            city_query = city_query.where(
                or_(
                    Job.country == "India",
                    Job.location.ilike("%india%"),
                )
            )
        elif "remote" in c_lower or "worldwide" in c_lower:
            city_query = city_query.where(
                or_(
                    Job.is_remote == True,
                    Job.country == "Remote / Worldwide",
                    Job.location.ilike("%remote%"),
                    Job.city.ilike("%remote%"),
                )
            )
        else:
            city_query = city_query.where(
                or_(
                    Job.country == country,
                    Job.country.ilike(f"%{country}%"),
                    Job.location.ilike(f"%{country}%"),
                )
            )

    city_rows = db.execute(
        city_query.group_by(Job.city).order_by(desc(func.count(Job.id))).limit(500)
    ).all()
    cities = [FacetItem(name=r[0], count=r[1]) for r in city_rows if r[0]]

    # Companies (Expanded limit to support all companies in search filter)
    comp_rows = db.execute(
        select(Job.company, func.count(Job.id))
        .where(Job.is_active == True)
        .group_by(Job.company)
        .order_by(desc(func.count(Job.id)))
        .limit(500)
    ).all()
    companies = [FacetItem(name=r[0], count=r[1]) for r in comp_rows if r[0]]

    # Sources
    src_rows = db.execute(
        select(JobSource.source_name, func.count(distinct(JobSource.job_id)))
        .join(Job, Job.id == JobSource.job_id)
        .where(Job.is_active == True)
        .group_by(JobSource.source_name)
        .order_by(desc(func.count(distinct(JobSource.job_id))))
    ).all()
    sources = [FacetItem(name=r[0], count=r[1]) for r in src_rows if r[0]]

    # Job Types
    jt_rows = db.execute(
        select(Job.job_type, func.count(Job.id))
        .where(Job.is_active == True, Job.job_type != None)
        .group_by(Job.job_type)
        .order_by(desc(func.count(Job.id)))
    ).all()
    job_types = [FacetItem(name=r[0], count=r[1]) for r in jt_rows if r[0]]

    # KPIs
    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    active_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True).scalar() or 0
    india_jobs = (
        db.query(func.count(Job.id))
        .filter(
            Job.is_active == True,
            or_(
                Job.country == "India",
                Job.location.ilike("%india%"),
            ),
        )
        .scalar()
        or 0
    )
    remote_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True, Job.is_remote == True).scalar() or 0
    saved_jobs = db.query(func.count(Job.id)).filter(Job.is_saved == True).scalar() or 0
    applied_jobs = (
        db.query(func.count(Job.id))
        .filter(Job.application_status.in_(["applied", "interview", "offer"]))
        .scalar()
        or 0
    )
    active_sources = db.query(func.count(distinct(JobSource.source_name))).scalar() or 0
    last_synced_at = db.query(func.max(ScrapeRun.finished_at)).scalar()

    return FiltersResponse(
        categories=categories,
        cities=cities,
        countries=countries,
        companies=companies,
        sources=sources,
        job_types=job_types,
        kpis=KpiMetrics(
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            india_jobs=india_jobs,
            remote_jobs=remote_jobs,
            saved_jobs=saved_jobs,
            applied_jobs=applied_jobs,
            active_sources=active_sources,
            last_synced_at=last_synced_at,
        ),
    )


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
