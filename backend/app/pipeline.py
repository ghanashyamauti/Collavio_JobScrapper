import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, or_
from rapidfuzz import fuzz

from app.database import SessionLocal, init_db
from app.models import Job, JobSource, ScrapeRun
from app.collectors.base import RawJob, BaseCollector
from app.collectors.jobspy_collector import JobSpyCollector
from app.collectors.ats_collector import ATSCollector
from app.collectors.public_feeds_collector import PublicFeedsCollector
from app.collectors.jsonld_collector import JSONLDCollector
from app.collectors.optional_apis_collector import OptionalAPIsCollector
from app.normalizer import (
    canonicalize_url,
    normalize_company,
    normalize_title,
    normalize_location_and_remote,
    detect_country,
    classify_category,
    parse_experience,
    clean_html_description,
    generate_fingerprint,
)

logger = logging.getLogger(__name__)

# Concurrency lock for background sync
_ingestion_lock = threading.Lock()
_current_sync_status: Dict[str, Any] = {
    "is_running": False,
    "active_collector": None,
    "last_started_at": None,
}


def get_sync_telemetry() -> Dict[str, Any]:
    """Returns real-time sync state."""
    return dict(_current_sync_status)


def process_raw_jobs(db: Session, raw_jobs: List[RawJob], collector_name: str) -> Tuple[int, int, int]:
    """
    Normalizes and ingests raw jobs using 3-tier deduplication and multi-source merging.
    Optimized with in-memory caching to eliminate per-job network latency on remote PostgreSQL.
    Returns (jobs_found, new_jobs, duplicates_merged).
    """
    jobs_found = len(raw_jobs)
    new_jobs = 0
    duplicates_merged = 0

    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)

    # Pre-load existing records in memory to eliminate remote roundtrips
    existing_jobs_by_fp: Dict[str, Job] = {}
    existing_jobs_by_source_url: Dict[Tuple[str, str], Job] = {}
    existing_jobs_by_source_extid: Dict[Tuple[str, str], Job] = {}
    jobs_by_company_city: Dict[Tuple[str, str], List[Job]] = {}
    seen_job_ids: Set[int] = set()
    scraped_companies: Set[str] = set()

    all_existing_jobs = db.execute(select(Job)).scalars().all()
    job_by_id = {job.id: job for job in all_existing_jobs}
    for job in all_existing_jobs:
        existing_jobs_by_fp[job.fingerprint_hash] = job
        comp_key = (job.normalized_company, (job.city or "").lower())
        jobs_by_company_city.setdefault(comp_key, []).append(job)

    all_existing_sources = db.execute(select(JobSource)).scalars().all()
    for src in all_existing_sources:
        job = job_by_id.get(src.job_id)
        if job:
            existing_jobs_by_source_url[(src.source_name, src.apply_url)] = job
            if src.external_id:
                existing_jobs_by_source_extid[(src.source_name, src.external_id)] = job

    for idx, raw in enumerate(raw_jobs):
        if not raw.title or not raw.company or not raw.apply_url:
            continue

        canonical_url = canonicalize_url(raw.apply_url)
        norm_comp = normalize_company(raw.company)
        norm_title = normalize_title(raw.title)
        clean_loc, standard_city, is_remote = normalize_location_and_remote(raw.location, raw.title)
        if raw.is_remote:
            is_remote = True
        country = detect_country(clean_loc, standard_city, is_remote)

        clean_desc = clean_html_description(raw.description)
        category = classify_category(raw.title, clean_desc)
        min_exp, max_exp = parse_experience(raw.title, clean_desc, raw.min_exp, raw.max_exp)
        is_explicit_exp = (raw.min_exp is not None or raw.max_exp is not None)
        fingerprint = generate_fingerprint(norm_comp, norm_title, standard_city)
        comp_city_key = (norm_comp, (standard_city or "").lower())

        # -------------------------------------------------------------
        # Tier 1: Exact Source Match (same source & apply_url/external_id)
        # -------------------------------------------------------------
        existing_job = existing_jobs_by_source_url.get((raw.source_name, canonical_url))
        if not existing_job and raw.external_id:
            existing_job = existing_jobs_by_source_extid.get((raw.source_name, raw.external_id))

        if existing_job:
            duplicates_merged += 1
            existing_job.is_active = True
            existing_job.updated_at = datetime.now(timezone.utc)
            if existing_job.id:
                seen_job_ids.add(existing_job.id)
            scraped_companies.add(norm_comp)
            if not existing_job.country or existing_job.country == "Global":
                existing_job.country = country
            _backfill_job_metadata(
                existing_job, clean_desc, raw.salary_min, raw.salary_max, raw.currency,
                min_exp, max_exp, is_explicit_exp
            )
            continue

        # -------------------------------------------------------------
        # Tier 2: Canonical Fingerprint Match
        # -------------------------------------------------------------
        existing_job = existing_jobs_by_fp.get(fingerprint)
        if existing_job:
            duplicates_merged += 1
            existing_job.is_active = True
            existing_job.updated_at = datetime.now(timezone.utc)
            if existing_job.id:
                seen_job_ids.add(existing_job.id)
            scraped_companies.add(norm_comp)
            if not existing_job.country or existing_job.country == "Global":
                existing_job.country = country
            _attach_source_and_backfill(
                db, existing_job, raw.source_name, raw.external_id, canonical_url,
                clean_desc, raw.salary_min, raw.salary_max, raw.currency, min_exp, max_exp,
                is_explicit_exp
            )
            existing_jobs_by_source_url[(raw.source_name, canonical_url)] = existing_job
            if raw.external_id:
                existing_jobs_by_source_extid[(raw.source_name, raw.external_id)] = existing_job
            continue

        # -------------------------------------------------------------
        # Tier 3: Fuzzy Cross-Board Match (rapidfuzz token_sort_ratio >= 86)
        # -------------------------------------------------------------
        recent_candidates = jobs_by_company_city.get(comp_city_key, [])
        fuzzy_matched_job = None
        for candidate in recent_candidates:
            # Quick length heuristic: if length difference is too high, token_sort_ratio cannot meet threshold
            if abs(len(norm_title) - len(candidate.normalized_title)) > 15:
                continue

            if candidate.created_at:
                c_created = candidate.created_at
                if c_created.tzinfo is None:
                    c_created = c_created.replace(tzinfo=timezone.utc)
                if c_created < fourteen_days_ago:
                    continue

            ratio = fuzz.token_sort_ratio(norm_title, candidate.normalized_title, score_cutoff=86)
            if ratio >= 86:
                fuzzy_matched_job = candidate
                break

        if fuzzy_matched_job:
            duplicates_merged += 1
            fuzzy_matched_job.is_active = True
            fuzzy_matched_job.updated_at = datetime.now(timezone.utc)
            if fuzzy_matched_job.id:
                seen_job_ids.add(fuzzy_matched_job.id)
            scraped_companies.add(norm_comp)
            if not fuzzy_matched_job.country or fuzzy_matched_job.country == "Global":
                fuzzy_matched_job.country = country
            _attach_source_and_backfill(
                db, fuzzy_matched_job, raw.source_name, raw.external_id, canonical_url,
                clean_desc, raw.salary_min, raw.salary_max, raw.currency, min_exp, max_exp,
                is_explicit_exp
            )
            existing_jobs_by_source_url[(raw.source_name, canonical_url)] = fuzzy_matched_job
            if raw.external_id:
                existing_jobs_by_source_extid[(raw.source_name, raw.external_id)] = fuzzy_matched_job
            continue

        # Clean job_type
        clean_job_type = raw.job_type
        if isinstance(clean_job_type, list):
            clean_job_type = ", ".join(str(x) for x in clean_job_type if x)
        elif clean_job_type:
            clean_job_type = str(clean_job_type)
        else:
            clean_job_type = None

        # -------------------------------------------------------------
        # Insert New Job Record
        # -------------------------------------------------------------
        new_job = Job(
            fingerprint_hash=fingerprint,
            title=raw.title.strip(),
            normalized_title=norm_title,
            company=raw.company.strip(),
            normalized_company=norm_comp,
            category=category,
            location=clean_loc,
            city=standard_city,
            country=country,
            is_remote=is_remote,
            is_active=True,
            min_exp=min_exp,
            max_exp=max_exp,
            job_type=clean_job_type,
            salary_min=raw.salary_min,
            salary_max=raw.salary_max,
            currency=raw.currency,
            description=clean_desc,
            posted_at=raw.posted_at or datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        new_source = JobSource(
            job=new_job,
            source_name=raw.source_name,
            external_id=raw.external_id,
            apply_url=canonical_url,
        )
        new_job.sources.append(new_source)
        db.add(new_job)

        # Use database SAVEPOINT to isolate any individual constraint conflict
        try:
            with db.begin_nested():
                db.flush([new_job, new_source])
        except Exception:
            existing_jobs_by_fp[fingerprint] = True
            continue

        # Register in in-memory lookups
        existing_jobs_by_fp[fingerprint] = new_job
        existing_jobs_by_source_url[(raw.source_name, canonical_url)] = new_job
        if raw.external_id:
            existing_jobs_by_source_extid[(raw.source_name, raw.external_id)] = new_job
        jobs_by_company_city.setdefault(comp_city_key, []).append(new_job)

        new_jobs += 1
        scraped_companies.add(norm_comp)

        if new_jobs % 250 == 0:
            try:
                db.commit()
            except Exception as commit_err:
                db.rollback()
                logger.warning(f"[Pipeline] Batch commit error: {commit_err}")

        if (idx + 1) % 500 == 0 or (idx + 1) == jobs_found:
            logger.info(f"[Pipeline] [{collector_name}] Processed {idx + 1}/{jobs_found} jobs ({new_jobs} new, {duplicates_merged} merged)...")

    # -------------------------------------------------------------
    # Automatic Job Deactivation for Direct Company/ATS Scraping
    # If a company board was scraped, any job in DB for that company not present in raw_jobs is expired/closed.
    # -------------------------------------------------------------
    deactivated_count = 0
    if collector_name in ("ats_direct", "dynamic_company") and scraped_companies:
        for job in all_existing_jobs:
            if (
                job.id
                and job.is_active
                and job.id not in seen_job_ids
                and job.normalized_company in scraped_companies
            ):
                # Verify that this job was sourced from this ATS scraper
                has_ats_source = any(
                    s.source_name in ("ats_direct", "dynamic_company", collector_name)
                    for s in getattr(job, "sources", [])
                )
                if has_ats_source:
                    job.is_active = False
                    job.updated_at = datetime.now(timezone.utc)
                    deactivated_count += 1
        if deactivated_count > 0:
            logger.info(
                f"[Pipeline] [{collector_name}] Deactivated {deactivated_count} closed/removed postings "
                f"across {len(scraped_companies)} companies."
            )

    try:
        db.commit()
    except Exception as commit_err:
        db.rollback()
        logger.warning(f"[Pipeline] Final commit handled conflict: {commit_err}")

    return jobs_found, new_jobs, duplicates_merged


def _backfill_job_metadata(
    job: Job,
    description: Optional[str],
    salary_min: Optional[float],
    salary_max: Optional[float],
    currency: Optional[str],
    min_exp: Optional[float],
    max_exp: Optional[float],
    is_explicit_exp: bool = False,
) -> None:
    """Enriches existing job if new source has richer data."""
    if description and (not job.description or len(description) > len(job.description)):
        job.description = description
    if salary_min is not None and (job.salary_min is None or salary_min < job.salary_min):
        job.salary_min = salary_min
    if salary_max is not None and (job.salary_max is None or salary_max > job.salary_max):
        job.salary_max = salary_max
    if currency and not job.currency:
        job.currency = currency
    if min_exp is not None:
        if job.min_exp is None or is_explicit_exp:
            job.min_exp = min_exp
    if max_exp is not None:
        if job.max_exp is None or is_explicit_exp:
            job.max_exp = max_exp


def _attach_source_and_backfill(
    db: Session,
    job: Job,
    source_name: str,
    external_id: Optional[str],
    apply_url: str,
    description: Optional[str],
    salary_min: Optional[float],
    salary_max: Optional[float],
    currency: Optional[str],
    min_exp: Optional[float],
    max_exp: Optional[float],
    is_explicit_exp: bool = False,
) -> None:
    """Attaches a new JobSource record to an existing job if not already present, and enriches metadata."""
    existing_src = next((s for s in job.sources if s.source_name == source_name), None)

    if not existing_src:
        new_src = JobSource(
            job=job,
            source_name=source_name,
            external_id=external_id,
            apply_url=apply_url,
        )
        job.sources.append(new_src)
        db.add(new_src)

    _backfill_job_metadata(job, description, salary_min, salary_max, currency, min_exp, max_exp, is_explicit_exp)


def deactivate_expired_jobs(db: Session, max_age_days: int = 30) -> int:
    """Marks jobs older than max_age_days without fresh sightings as inactive."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    expired_jobs = db.execute(
        select(Job).where(Job.is_active == True, Job.posted_at != None, Job.posted_at < cutoff)
    ).scalars().all()
    count = 0
    for j in expired_jobs:
        j.is_active = False
        j.updated_at = datetime.now(timezone.utc)
        count += 1
    if count:
        db.commit()
        logger.info(f"[Pipeline] Marked {count} jobs older than {max_age_days} days as inactive/expired.")
    return count


def run_ingestion(
    sources: Optional[List[str]] = None,
    mode: str = "full",
    queries: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    country: Optional[str] = "India",
) -> List[Dict[str, Any]]:
    """
    Main orchestration entrypoint for background or CLI sync.
    Runs collectors, logs ScrapeRun records, and manages the ingestion lock.
    Supports dynamic queries and locations for live targeted harvesting.
    """
    if not _ingestion_lock.acquire(blocking=False):
        logger.warning("[Pipeline] Ingestion is already running in another thread, skipping.")
        return []

    global _current_sync_status
    _current_sync_status["is_running"] = True
    _current_sync_status["last_started_at"] = datetime.now(timezone.utc)

    init_db()
    db = SessionLocal()
    summary: List[Dict[str, Any]] = []

    try:
        collectors_to_run: List[BaseCollector] = []

        if sources:
            source_set = set(s.strip().lower() for s in sources)
            if "jobspy" in source_set:
                collectors_to_run.append(
                    JobSpyCollector(queries=queries, locations=locations, country_indeed=country)
                )
            if "ats_direct" in source_set or "ats" in source_set:
                collectors_to_run.append(ATSCollector())
            if "public_feeds" in source_set or "feeds" in source_set:
                collectors_to_run.append(PublicFeedsCollector())
            if "jsonld" in source_set:
                collectors_to_run.append(JSONLDCollector())
            if "optional_apis" in source_set or "apis" in source_set:
                collectors_to_run.append(OptionalAPIsCollector())
        else:
            # Mode fast: ATS + Public Feeds + Optional APIs + JSON-LD
            # Mode full: includes JobSpy with dynamic or configured queries
            collectors_to_run.append(ATSCollector())
            collectors_to_run.append(PublicFeedsCollector())
            collectors_to_run.append(OptionalAPIsCollector())
            collectors_to_run.append(JSONLDCollector())
            if mode == "full":
                collectors_to_run.append(
                    JobSpyCollector(queries=queries, locations=locations, country_indeed=country)
                )

        for collector in collectors_to_run:
            _current_sync_status["active_collector"] = collector.name
            scrape_run = ScrapeRun(
                source=collector.name,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.add(scrape_run)
            db.commit()

            try:
                logger.info(f"[Pipeline] Executing collector '{collector.name}'...")
                raw_jobs = collector.collect()
                found, new, merged = process_raw_jobs(db, raw_jobs, collector.name)

                scrape_run.jobs_found = found
                scrape_run.new_jobs = new
                scrape_run.duplicates_merged = merged
                scrape_run.status = "success"
                scrape_run.finished_at = datetime.now(timezone.utc)
                db.commit()

                res = {
                    "collector": collector.name,
                    "status": "success",
                    "jobs_found": found,
                    "new_jobs": new,
                    "duplicates_merged": merged,
                }
                summary.append(res)
                logger.info(f"[Pipeline] '{collector.name}' complete: {res}")
            except Exception as e:
                logger.error(f"[Pipeline] Collector '{collector.name}' failed: {e}", exc_info=True)
                scrape_run.status = "failed"
                scrape_run.error_message = str(e)
                scrape_run.finished_at = datetime.now(timezone.utc)
                db.commit()
                summary.append({
                    "collector": collector.name,
                    "status": "failed",
                    "error": str(e),
                })

        # Automatically mark jobs older than 30 days without updates as expired/inactive
        try:
            deactivate_expired_jobs(db, max_age_days=30)
        except Exception as exp_err:
            logger.warning(f"[Pipeline] Stale job expiration check failed: {exp_err}")

    finally:
        _current_sync_status["is_running"] = False
        _current_sync_status["active_collector"] = None
        db.close()
        _ingestion_lock.release()

    return summary
