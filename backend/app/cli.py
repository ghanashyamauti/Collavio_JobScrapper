import argparse
import sys
import logging
from sqlalchemy import select, func, text, desc
from app.database import SessionLocal, init_db, DB_TYPE
from app.models import Job, JobSource
from app.pipeline import run_ingestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cli")


def print_database_stats():
    """Prints comprehensive database stats including top countries, Indian cities, sources, and storage size."""
    init_db()
    db = SessionLocal()
    try:
        total_active = db.execute(select(func.count(Job.id)).where(Job.is_active == True)).scalar() or 0
        total_inactive = db.execute(select(func.count(Job.id)).where(Job.is_active == False)).scalar() or 0
        total_jobs = total_active + total_inactive

        print("\n" + "=" * 60)
        print("           COLLAVIO JOBS - DATABASE TELEMETRY")
        print("=" * 60)
        print(f"Engine Type:          {DB_TYPE}")
        print(f"Total Jobs in DB:     {total_jobs:,}")
        print(f"Active Live Jobs:     {total_active:,}")
        print(f"Inactive / Expired:   {total_inactive:,}")

        # Storage size for PostgreSQL
        if "postgres" in DB_TYPE.lower():
            try:
                size_bytes = db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
                size_mb = size_bytes / (1024 * 1024)
                print(f"Database Size on Disk: {size_mb:.2f} MB")
            except Exception as e:
                print(f"Database Size:        N/A ({e})")

        # Breakdown by Source
        print("\n--- ACTIVE JOBS BY SOURCE ---")
        source_counts = (
            db.execute(
                select(JobSource.source_name, func.count(JobSource.id))
                .join(Job, Job.id == JobSource.job_id)
                .where(Job.is_active == True)
                .group_by(JobSource.source_name)
                .order_by(desc(func.count(JobSource.id)))
            )
            .all()
        )
        for sname, cnt in source_counts:
            print(f"  • {sname:20}: {cnt:,}")

        # Top 10 Countries
        print("\n--- TOP 10 COUNTRIES ---")
        country_counts = (
            db.execute(
                select(Job.country, func.count(Job.id))
                .where(Job.is_active == True, Job.country != None, Job.country != "")
                .group_by(Job.country)
                .order_by(desc(func.count(Job.id)))
                .limit(10)
            )
            .all()
        )
        for country, cnt in country_counts:
            print(f"  • {country:20}: {cnt:,}")

        # Top 15 Indian Cities
        print("\n--- TOP 15 INDIAN CITIES ---")
        indian_cities = (
            db.execute(
                select(Job.city, func.count(Job.id))
                .where(
                    Job.is_active == True,
                    Job.country == "India",
                    Job.city != None,
                    Job.city != "",
                    Job.city != "Remote",
                )
                .group_by(Job.city)
                .order_by(desc(func.count(Job.id)))
                .limit(15)
            )
            .all()
        )
        for city, cnt in indian_cities:
            print(f"  • {city:20}: {cnt:,}")

        print("=" * 60 + "\n")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Collavio Jobs CLI Ingestion & Stats Tool")
    parser.add_argument(
        "--sources",
        type=str,
        default="ats_direct,public_feeds,workday",
        help="Comma-separated list of sources to run: ats_direct, public_feeds, workday, optional_apis, jobspy",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="fast",
        choices=["fast", "full"],
        help="Ingestion mode ('fast' skips JobSpy by default, 'full' runs everything)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only display current database telemetry and exit",
    )

    args = parser.parse_args()

    if args.stats_only:
        print_database_stats()
        return

    source_list = [s.strip() for s in args.sources.split(",") if s.strip()]
    logger.info(f"Starting ingestion with sources: {source_list} (mode={args.mode})")

    results = run_ingestion(sources=source_list, mode=args.mode)
    logger.info(f"Ingestion completed. Summary: {results}")

    # Display final verified telemetry
    print_database_stats()


if __name__ == "__main__":
    main()
