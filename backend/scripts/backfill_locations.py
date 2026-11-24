import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update, func, text
from app.database import SessionLocal
from app.models import Job
from app.normalizer import normalize_location_and_remote, detect_country

def backfill_locations():
    db = SessionLocal()
    try:
        print("Querying jobs needing location/country refinement...", flush=True)
        t0 = time.time()
        
        # Target jobs in India, Global, or with missing/unresolved country or city
        stmt = (
            select(Job.id, Job.location, Job.city, Job.country, Job.is_remote)
            .where(
                Job.is_active == True,
                (
                    Job.country.in_(["India", "Global"])
                    | (Job.country == None)
                    | Job.city.in_(["In", "India", "Nashville", "Indianapolis", "Plainfield", "Greenfield", "Memphis", "Atlanta"])
                )
            )
        )
        candidates = db.execute(stmt).all()
        print(f"Found {len(candidates):,} candidate jobs to inspect.", flush=True)

        updates = []
        for j_id, loc, old_city, old_country, old_remote in candidates:
            clean_loc, new_city, is_rem = normalize_location_and_remote(loc)
            new_country = detect_country(clean_loc, new_city, is_rem)

            if new_country != old_country or new_city != old_city:
                updates.append({
                    "id": j_id,
                    "country": new_country,
                    "city": new_city,
                    "is_remote": is_rem,
                })

        print(f"Identified {len(updates):,} jobs needing updates. Committing in batches...", flush=True)

        # Bulk update in batches of 1000
        batch_size = 1000
        updated_total = 0
        for i in range(0, len(updates), batch_size):
            chunk = updates[i : i + batch_size]
            db.bulk_update_mappings(Job, chunk)
            db.commit()
            updated_total += len(chunk)
            print(f"  • Updated {updated_total:,} / {len(updates):,} jobs...", flush=True)

        elapsed = time.time() - t0
        print(f"\nLocation & Country refinement complete in {elapsed:.1f}s! Total jobs modified: {updated_total:,}", flush=True)

        # Print new Top 20 Countries
        print("\n" + "=" * 60)
        print("           UPDATED TOP 20 COUNTRIES")
        print("=" * 60)
        top_countries = db.execute(text("""
            SELECT country, count(id)
            FROM jobs
            WHERE is_active = TRUE
            GROUP BY country
            ORDER BY count(id) DESC
            LIMIT 20
        """)).all()
        for cname, cnt in top_countries:
            print(f"  • {cname or 'NULL':25}: {cnt:,}")

        print("\n" + "=" * 60)
        print("           UPDATED TOP 15 INDIAN CITIES")
        print("=" * 60)
        top_in_cities = db.execute(text("""
            SELECT city, count(id)
            FROM jobs
            WHERE is_active = TRUE AND country = 'India' AND city != 'Remote' AND city IS NOT NULL
            GROUP BY city
            ORDER BY count(id) DESC
            LIMIT 15
        """)).all()
        for cname, cnt in top_in_cities:
            print(f"  • {cname or 'NULL':25}: {cnt:,}")

    finally:
        db.close()

if __name__ == "__main__":
    backfill_locations()
