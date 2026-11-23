import sys
import os
import re

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, init_db
from app.models import Job
from app.normalizer import clean_html_description, detect_country
from sqlalchemy import select

def backfill():
    print("Connecting to Neon PostgreSQL...")
    init_db()
    db = SessionLocal()
    try:
        jobs = db.execute(select(Job)).scalars().all()
        print(f"Total jobs in database: {len(jobs)}")

        updated_desc = 0
        updated_country = 0
        country_counts = {}

        for job in jobs:
            # 1. Clean description if it contains entity escapes or raw html
            orig_desc = job.description or ""
            if any(marker in orig_desc for marker in ["&lt;", "&gt;", "&#39;", "&quot;", "&amp;", "<p>", "<div>", "<li>", "<br", "<strong", "<ul>"]):
                cleaned = clean_html_description(orig_desc)
                if cleaned != orig_desc:
                    job.description = cleaned
                    updated_desc += 1

            # 2. Backfill country
            new_country = detect_country(job.location, job.city, job.is_remote)
            if job.country != new_country:
                job.country = new_country
                updated_country += 1

            c_name = job.country or "Unspecified"
            country_counts[c_name] = country_counts.get(c_name, 0) + 1

        db.commit()
        print(f"Backfill Complete!")
        print(f"- Cleaned descriptions: {updated_desc}")
        print(f"- Updated countries: {updated_country}")
        print("Country distribution in Neon DB:")
        for c, count in sorted(country_counts.items(), key=lambda x: -x[1]):
            print(f"  {c}: {count}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill()
