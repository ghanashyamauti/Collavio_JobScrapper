import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, update, func
from rapidfuzz import fuzz

from app.database import SessionLocal, init_db, engine
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
    detect_platform_source,
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


def _bulk_upsert_chunk(
    db: Session,
    jobs_chunk: List[Dict[str, Any]],
    sources_chunk: List[Dict[str, Any]],
) -> Tuple[int, int]:
    """
    Executes a high-speed bulk upsert into jobs and job_sources using native
    PostgreSQL ON CONFLICT DO UPDATE (or SQLite fallback for test suites).
    Returns (new_inserted, duplicates_updated).
    """
    if not jobs_chunk:
        return 0, 0

    dialect_name = db.bind.dialect.name if db.bind else "postgresql"
    new_count = 0
    merged_count = 0

    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # 1. Bulk Upsert into jobs table
        stmt = pg_insert(Job).values(jobs_chunk)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[Job.fingerprint_hash],
            set_={
                "is_active": True,
                "updated_at": func.now(),
                "country": func.coalesce(Job.country, stmt.excluded.country),
                "salary_min": func.coalesce(stmt.excluded.salary_min, Job.salary_min),
                "salary_max": func.coalesce(stmt.excluded.salary_max, Job.salary_max),
                "currency": func.coalesce(stmt.excluded.currency, Job.currency),
                "min_exp": func.coalesce(stmt.excluded.min_exp, Job.min_exp),
                "max_exp": func.coalesce(stmt.excluded.max_exp, Job.max_exp),
                "description": func.coalesce(Job.description, stmt.excluded.description),
            },
        ).returning(
            Job.id,
            Job.fingerprint_hash,
            (Job.created_at == Job.updated_at).label("is_new"),
        )

        res = db.execute(upsert_stmt).all()
        fp_to_id = {}
        for row in res:
            job_id, fp, is_new = row[0], row[1], row[2]
            fp_to_id[fp] = job_id
            if is_new:
                new_count += 1
            else:
                merged_count += 1

        # 2. Bulk Upsert into job_sources table
        valid_sources = []
        seen_keys: Set[Tuple[int, str]] = set()
        for src in sources_chunk:
            fp = src.get("fingerprint_hash")
            job_id = fp_to_id.get(fp)
            if not job_id:
                continue
            key = (job_id, src["source_name"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            valid_sources.append({
                "job_id": job_id,
                "source_name": src["source_name"],
                "external_id": src.get("external_id"),
                "apply_url": src["apply_url"],
                "scraped_at": func.now(),
            })

        if valid_sources:
            src_stmt = pg_insert(JobSource).values(valid_sources)
            upsert_src = src_stmt.on_conflict_do_update(
                constraint="uq_job_source",
                set_={
                    "apply_url": src_stmt.excluded.apply_url,
                    "scraped_at": func.now(),
                },
            )
            db.execute(upsert_src)

    else:
        # SQLite dialect (in-memory test harness)
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        stmt = sqlite_insert(Job).values(jobs_chunk)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[Job.fingerprint_hash],
            set_={
                "is_active": True,
                "updated_at": func.now(),
                "country": func.coalesce(Job.country, stmt.excluded.country),
                "salary_min": func.coalesce(stmt.excluded.salary_min, Job.salary_min),
                "salary_max": func.coalesce(stmt.excluded.salary_max, Job.salary_max),
                "currency": func.coalesce(stmt.excluded.currency, Job.currency),
                "min_exp": func.coalesce(stmt.excluded.min_exp, Job.min_exp),
                "max_exp": func.coalesce(stmt.excluded.max_exp, Job.max_exp),
                "description": func.coalesce(Job.description, stmt.excluded.description),
            },
        ).returning(Job.id, Job.fingerprint_hash)

        res = db.execute(upsert_stmt).all()
        fp_to_id = {row[1]: row[0] for row in res}
        new_count = len(res)

        valid_sources = []
        seen_keys = set()
        for src in sources_chunk:
            fp = src.get("fingerprint_hash")
            job_id = fp_to_id.get(fp)
            if not job_id:
                continue
            key = (job_id, src["source_name"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            valid_sources.append({
                "job_id": job_id,
                "source_name": src["source_name"],
                "external_id": src.get("external_id"),
                "apply_url": src["apply_url"],
                "scraped_at": func.now(),
            })

        if valid_sources:
            src_stmt = sqlite_insert(JobSource).values(valid_sources)
            upsert_src = src_stmt.on_conflict_do_update(
                index_elements=[JobSource.job_id, JobSource.source_name],
                set_={
                    "apply_url": src_stmt.excluded.apply_url,
                    "scraped_at": func.now(),
                },
            )
            db.execute(upsert_src)

    db.commit()
    return new_count, merged_count


def process_raw_jobs(
    db: Optional[Session],
    raw_jobs: List[RawJob],
    collector_name: str,
    chunk_size: int = 1000,
) -> Tuple[int, int, int]:
    """
    Normalizes, deduplicates in-memory, and writes jobs in resilient 1,000-row chunks
    using native PostgreSQL bulk upserts with zero per-row roundtrips.
    Returns (jobs_found, new_jobs, duplicates_merged).
    """
    jobs_found = len(raw_jobs)
    if jobs_found == 0:
        return 0, 0, 0

    logger.info(f"[Pipeline] [{collector_name}] Normalizing & deduplicating {jobs_found} raw postings in memory...")

    # Step 1: In-memory normalization and deduplication by fingerprint_hash
    unique_jobs: Dict[str, Dict[str, Any]] = {}
    unique_sources: List[Dict[str, Any]] = []
    seen_source_urls: Dict[Tuple[str, str], str] = {}
    scraped_companies: Set[str] = set()
    seen_fingerprints: Set[str] = set()

    # Pre-index fuzzy clusters within this batch by (norm_company, city)
    clusters: Dict[Tuple[str, str], List[str]] = {}

    for raw in raw_jobs:
        if not raw.title or not raw.company or not raw.apply_url:
            continue

        canonical_url = canonicalize_url(raw.apply_url)
        norm_comp = normalize_company(raw.company)
        norm_title = normalize_title(raw.title)
        clean_loc, standard_city, is_remote = normalize_location_and_remote(raw.location, raw.title)
        if raw.is_remote:
            is_remote = True
        country = detect_country(clean_loc, standard_city, is_remote)

        # Lightweight description: clean only if short/provided, else None for on-demand fetch
        clean_desc = None
        if raw.description:
            clean_desc = clean_html_description(raw.description)

        category = classify_category(raw.title, clean_desc or "")
        min_exp, max_exp = parse_experience(raw.title, clean_desc or "", raw.min_exp, raw.max_exp)
        fingerprint = generate_fingerprint(norm_comp, norm_title, standard_city)
        comp_city_key = (norm_comp, (standard_city or "").lower())

        clean_job_type = raw.job_type
        if isinstance(clean_job_type, list):
            clean_job_type = ", ".join(str(x) for x in clean_job_type if x)
        elif clean_job_type:
            clean_job_type = str(clean_job_type)

        scraped_companies.add(norm_comp)
        seen_fingerprints.add(fingerprint)

        # Check URL match or existing fingerprint in current batch
        target_fp = fingerprint
        if (raw.source_name, canonical_url) in seen_source_urls:
            target_fp = seen_source_urls[(raw.source_name, canonical_url)]
        elif fingerprint not in unique_jobs and comp_city_key in clusters:
            # Check fuzzy match against cluster candidates
            for candidate_fp in clusters[comp_city_key]:
                cand = unique_jobs.get(candidate_fp)
                if cand and abs(len(norm_title) - len(cand["normalized_title"])) <= 12:
                    if fuzz.token_sort_ratio(norm_title, cand["normalized_title"]) >= 88:
                        target_fp = candidate_fp
                        break

        seen_source_urls[(raw.source_name, canonical_url)] = target_fp

        if target_fp not in unique_jobs:
            unique_jobs[target_fp] = {
                "fingerprint_hash": target_fp,
                "title": raw.title.strip()[:250],
                "normalized_title": norm_title[:250],
                "company": raw.company.strip()[:250],
                "normalized_company": norm_comp[:250],
                "category": category[:100],
                "location": clean_loc[:250] if clean_loc else None,
                "city": standard_city[:100] if standard_city else None,
                "country": country[:100] if country else None,
                "is_remote": is_remote,
                "is_active": True,
                "min_exp": min_exp,
                "max_exp": max_exp,
                "job_type": clean_job_type[:50] if clean_job_type else None,
                "salary_min": raw.salary_min,
                "salary_max": raw.salary_max,
                "currency": raw.currency[:10] if raw.currency else None,
                "description": clean_desc,
                "posted_at": raw.posted_at or datetime.now(timezone.utc),
            }
            clusters.setdefault(comp_city_key, []).append(target_fp)
        else:
            # Merge richer attributes into in-memory job
            existing = unique_jobs[target_fp]
            if raw.salary_min and (not existing["salary_min"] or raw.salary_min < existing["salary_min"]):
                existing["salary_min"] = raw.salary_min
            if raw.salary_max and (not existing["salary_max"] or raw.salary_max > existing["salary_max"]):
                existing["salary_max"] = raw.salary_max
            if not existing["currency"] and raw.currency:
                existing["currency"] = raw.currency[:10]
            if clean_desc and not existing["description"]:
                existing["description"] = clean_desc

        platform = detect_platform_source(raw.source_name, canonical_url)
        unique_sources.append({
            "fingerprint_hash": target_fp,
            "source_name": platform[:100],
            "external_id": (raw.external_id or "")[:250] if raw.external_id else None,
            "apply_url": canonical_url,
        })

    logger.info(
        f"[Pipeline] [{collector_name}] In-memory preparation complete: "
        f"{len(unique_jobs)} unique jobs, {len(unique_sources)} sources."
    )

    # Step 2: Ingest in chunks of 1,000 items with fresh sessions
    all_job_items = list(unique_jobs.values())
    sources_by_fp: Dict[str, List[Dict[str, Any]]] = {}
    for s in unique_sources:
        sources_by_fp.setdefault(s["fingerprint_hash"], []).append(s)

    total_new = 0
    total_merged = 0

    use_external_session = db is not None
    chunks = [all_job_items[i : i + chunk_size] for i in range(0, len(all_job_items), chunk_size)]

    for chunk_idx, job_chunk in enumerate(chunks, 1):
        chunk_sources = []
        for j in job_chunk:
            chunk_sources.extend(sources_by_fp.get(j["fingerprint_hash"], []))

        if use_external_session:
            n, m = _bulk_upsert_chunk(db, job_chunk, chunk_sources)
            total_new += n
            total_merged += m
        else:
            with SessionLocal() as session:
                n, m = _bulk_upsert_chunk(session, job_chunk, chunk_sources)
                total_new += n
                total_merged += m

        logger.info(
            f"[Pipeline] [{collector_name}] Upserted chunk {chunk_idx}/{len(chunks)} "
            f"({len(job_chunk)} jobs) -> total new: {total_new}, merged: {total_merged}"
        )

    # Step 3: Bulk reconciliation for live job removal
    # If this was a direct employer board scrape with successful response, mark missing roles inactive
    if collector_name in ("ats_direct", "dynamic_company", "workday") and scraped_companies and seen_fingerprints:
        try:
            recon_session = db if use_external_session else SessionLocal()
            stmt = (
                update(Job)
                .where(
                    Job.normalized_company.in_(list(scraped_companies)),
                    Job.fingerprint_hash.not_in(list(seen_fingerprints)),
                    Job.is_active == True,
                )
                .values(is_active=False, updated_at=func.now())
            )
            recon_session.execute(stmt)
            recon_session.commit()
            if not use_external_session:
                recon_session.close()
            logger.info(f"[Pipeline] [{collector_name}] Bulk reconciliation deactivated closed roles.")
        except Exception as recon_err:
            logger.warning(f"[Pipeline] Bulk reconciliation skipped or failed: {recon_err}")

    return jobs_found, total_new, total_merged


def deactivate_expired_jobs(db: Session, max_age_days: int = 14) -> int:
    """Marks untracked postings older than max_age_days without fresh updates as inactive."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    stmt = (
        update(Job)
        .where(
            Job.is_active == True,
            Job.updated_at < cutoff,
            Job.is_saved == False,
            or_(Job.application_status == None, Job.application_status == "none"),
        )
        .values(is_active=False, updated_at=func.now())
    )
    result = db.execute(stmt)
    db.commit()
    count = result.rowcount if hasattr(result, "rowcount") else 0
    if count > 0:
        logger.info(f"[Pipeline] Deactivated {count} untracked stale jobs older than {max_age_days} days.")
    return count


def run_ingestion(
    sources: Optional[List[str]] = None,
    mode: str = "fast",
    queries: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    country: str = "india",
) -> List[Dict[str, Any]]:
    """
    Main orchestration entrypoint for background or CLI sync.
    Runs collectors, logs ScrapeRun records, and manages the ingestion lock.
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
            if "ats_direct" in source_set or "ats" in source_set:
                collectors_to_run.append(ATSCollector())
            if "public_feeds" in source_set or "feeds" in source_set:
                collectors_to_run.append(PublicFeedsCollector())
            if "workday" in source_set:
                try:
                    from app.collectors.workday_collector import WorkdayCollector
                    collectors_to_run.append(WorkdayCollector())
                except ImportError:
                    pass
            if "optional_apis" in source_set or "apis" in source_set:
                collectors_to_run.append(OptionalAPIsCollector())
            if "jsonld" in source_set:
                collectors_to_run.append(JSONLDCollector())
            if "jobspy" in source_set:
                collectors_to_run.append(
                    JobSpyCollector(queries=queries, locations=locations, country_indeed=country)
                )
        else:
            collectors_to_run.append(ATSCollector())
            try:
                from app.collectors.workday_collector import WorkdayCollector
                collectors_to_run.append(WorkdayCollector())
            except ImportError:
                pass
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
                found, new, merged = process_raw_jobs(None, raw_jobs, collector.name)

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

        try:
            deactivate_expired_jobs(db, max_age_days=14)
        except Exception as exp_err:
            logger.warning(f"[Pipeline] Stale job expiration check failed: {exp_err}")

    finally:
        _current_sync_status["is_running"] = False
        _current_sync_status["active_collector"] = None
        db.close()
        _ingestion_lock.release()

    return summary
