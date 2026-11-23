import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, init_db
from app.models import Job
from app.normalizer import classify_category
from sqlalchemy import select, func

def reclassify():
    print("Connecting to Neon PostgreSQL...", flush=True)
    init_db()
    db = SessionLocal()
    try:
        jobs = db.execute(select(Job)).scalars().all()
        print(f"Total jobs to inspect: {len(jobs)}", flush=True)

        updated_count = 0
        cat_counts = {}

        for job in jobs:
            new_cat = classify_category(job.title, job.description)
            if job.category != new_cat:
                job.category = new_cat
                updated_count += 1
            cat_counts[new_cat] = cat_counts.get(new_cat, 0) + 1

        db.commit()
        print(f"Reclassification complete! Updated {updated_count} jobs.", flush=True)
        print("\nNew Category Distribution in Neon DB:", flush=True)
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {cnt}", flush=True)
    finally:
        db.close()

if __name__ == "__main__":
    reclassify()
