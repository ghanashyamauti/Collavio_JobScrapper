import os
import sys
import logging
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, SessionLocal, engine
from app.collectors.ats_collector import ATSCollector
from app.collectors.public_feeds_collector import PublicFeedsCollector
from app.pipeline import process_raw_jobs
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bulk_harvester")

def main():
    logger.info("=== Starting High-Volume Bulk Ingestion Run ===")
    init_db()
    start_time = time.time()

    total_found = 0
    total_new = 0
    total_merged = 0

    try:
        # Phase 1: High-Speed Concurrent ATS Collector (250+ companies)
        logger.info("[Phase 1/2] Harvesting 250+ Global & Indian Tech Companies via Direct ATS APIs...")
        ats = ATSCollector()
        ats_jobs = ats.collect()
        logger.info(f"[Phase 1/2] ATS Collector returned {len(ats_jobs)} raw job postings.")
        if ats_jobs:
            with SessionLocal() as db:
                f, n, m = process_raw_jobs(db, ats_jobs, collector_name="ats_direct")
                total_found += f
                total_new += n
                total_merged += m
                logger.info(f"[Phase 1/2] ATS Ingest complete: {n} new jobs, {m} merged duplicates.")

        # Phase 2: Public High-Volume Feeds (Arbeitnow 25 pages + Himalayas + Remotive + Jobicy)
        logger.info("[Phase 2/2] Harvesting Multi-Page Public Feeds (Arbeitnow 25 pages, Himalayas, Remotive, Jobicy)...")
        feeds = PublicFeedsCollector()
        feed_jobs = feeds.collect()
        logger.info(f"[Phase 2/2] Public Feeds returned {len(feed_jobs)} raw job postings.")
        if feed_jobs:
            with SessionLocal() as db:
                f, n, m = process_raw_jobs(db, feed_jobs, collector_name="public_feeds")
                total_found += f
                total_new += n
                total_merged += m
                logger.info(f"[Phase 2/2] Feeds Ingest complete: {n} new jobs, {m} merged duplicates.")

        elapsed = time.time() - start_time
        logger.info(f"=== Bulk Ingestion Complete in {elapsed:.1f}s ===")
        logger.info(f"Total raw fetched: {total_found} | New jobs saved: {total_new} | Merged: {total_merged}")

    except Exception as e:
        logger.error(f"Bulk ingestion error: {e}", exc_info=True)

    # Query latest DB stats
    with engine.connect() as conn:
        db_size_res = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database())), pg_database_size(current_database())")).fetchone()
        jobs_res = conn.execute(text("SELECT pg_size_pretty(pg_total_relation_size('jobs')), count(*) FROM jobs")).fetchone()
        active_res = conn.execute(text("SELECT count(*) FROM jobs WHERE is_active = true")).scalar()

        total_mb = db_size_res[1] / (1024 * 1024)
        print("\n" + "=" * 50)
        print("LATEST DATABASE METRICS AFTER BULK HARVEST")
        print("=" * 50)
        print(f"Total Active Jobs: {active_res:,}")
        print(f"Total Database Rows: {jobs_res[1]:,}")
        print(f"Total DB Size: {db_size_res[0]} ({total_mb:.2f} MB)")
        print(f"Neon Free Tier Limit: 512 MB")
        print(f"Remaining Available on Neon: {512 - total_mb:.2f} MB ({(512 - total_mb) / 512 * 100:.1f}% free)")
        print("=" * 50)

if __name__ == "__main__":
    main()
