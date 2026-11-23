import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, init_db
from app.collectors.ats_collector import ATSCollector
from app.pipeline import process_raw_jobs
from app.models import Job
from sqlalchemy import select, func, desc

def sync():
    print("Initializing DB...")
    init_db()
    collector = ATSCollector()
    print(f"Collecting jobs from Greenhouse ({collector.greenhouse_boards}) and Lever ({collector.lever_boards})...")
    raw_jobs = collector.collect()
    print(f"Collected {len(raw_jobs)} raw jobs from ATS boards.")

    db = SessionLocal()
    try:
        found, new_cnt, merged_cnt = process_raw_jobs(db, raw_jobs, "ats_direct")
        print(f"Ingestion done: found={found}, new={new_cnt}, merged={merged_cnt}")

        # Check current city breakdown
        city_rows = db.execute(
            select(Job.city, func.count(Job.id))
            .where(Job.is_active == True, Job.city != None)
            .group_by(Job.city)
            .order_by(desc(func.count(Job.id)))
        ).all()
        print("\nUpdated Cities in Neon DB:")
        for r in city_rows[:15]:
            print(f"  {r[0]}: {r[1]}")

        # Check India jobs
        india_cnt = db.execute(select(func.count(Job.id)).where(Job.country == "India")).scalar()
        print(f"\nTotal India jobs in Neon DB now: {india_cnt}")
    finally:
        db.close()

if __name__ == "__main__":
    sync()
