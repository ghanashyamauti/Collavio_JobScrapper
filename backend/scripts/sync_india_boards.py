import sys
import os
import httpx
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, init_db
from app.collectors.base import RawJob
from app.pipeline import process_raw_jobs
from app.models import Job
from sqlalchemy import select, func, desc

def harvest_india_ats():
    print("Initializing Neon DB...", flush=True)
    init_db()

    gh_slugs = ["pubmatic", "ensono", "rubrik", "zocdoc", "druva", "ivalua", "inmobi", "groww"]
    lever_slugs = ["mindtickle"]

    raw_jobs = []
    headers = {"User-Agent": "JobPulse/1.0", "Accept": "application/json"}

    with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
        # Greenhouse
        for slug in gh_slugs:
            try:
                url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
                print(f"Fetching Greenhouse '{slug}'...", flush=True)
                r = client.get(url)
                if r.status_code == 200:
                    jobs = r.json().get("jobs", [])
                    print(f"  -> Got {len(jobs)} jobs for {slug}", flush=True)
                    company_name = slug.capitalize()
                    for item in jobs:
                        title = (item.get("title") or "").strip()
                        apply_url = item.get("absolute_url")
                        if not title or not apply_url:
                            continue
                        loc_name = item.get("location", {}).get("name") if isinstance(item.get("location"), dict) else str(item.get("location") or "")
                        desc = item.get("content") or ""
                        raw_jobs.append(
                            RawJob(
                                source_name="greenhouse",
                                external_id=f"gh_{slug}_{item.get('id')}",
                                title=title,
                                company=company_name,
                                apply_url=apply_url,
                                location=loc_name,
                                is_remote="remote" in loc_name.lower(),
                                description=desc,
                            )
                        )
            except Exception as e:
                print(f"Error fetching {slug}: {e}", flush=True)

        # Lever
        for slug in lever_slugs:
            try:
                url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
                print(f"Fetching Lever '{slug}'...", flush=True)
                r = client.get(url)
                if r.status_code == 200:
                    jobs = r.json()
                    if isinstance(jobs, list):
                        print(f"  -> Got {len(jobs)} jobs for {slug}", flush=True)
                        for item in jobs:
                            title = (item.get("text") or "").strip()
                            apply_url = item.get("hostedUrl") or item.get("applyUrl")
                            if not title or not apply_url:
                                continue
                            loc_name = item.get("categories", {}).get("location") or ""
                            desc = item.get("description") or ""
                            raw_jobs.append(
                                RawJob(
                                    source_name="lever",
                                    external_id=f"lever_{slug}_{item.get('id')}",
                                    title=title,
                                    company=slug.capitalize(),
                                    apply_url=apply_url,
                                    location=loc_name,
                                    is_remote="remote" in loc_name.lower(),
                                    description=desc,
                                )
                            )
            except Exception as e:
                print(f"Error fetching {slug}: {e}", flush=True)

    print(f"\nTotal raw jobs to process: {len(raw_jobs)}", flush=True)

    db = SessionLocal()
    try:
        found, new_cnt, merged_cnt = process_raw_jobs(db, raw_jobs, "ats_direct")
        print(f"Ingestion complete: found={found}, new={new_cnt}, merged={merged_cnt}", flush=True)

        # Check Pune & Mumbai
        pune = db.execute(select(func.count(Job.id)).where(Job.city == "Pune")).scalar()
        mumbai = db.execute(select(func.count(Job.id)).where(Job.city == "Mumbai")).scalar()
        india = db.execute(select(func.count(Job.id)).where(Job.country == "India")).scalar()
        total = db.execute(select(func.count(Job.id))).scalar()
        print(f"\nNeon DB Status: Total={total} | India={india} | Pune={pune} | Mumbai={mumbai}", flush=True)

        print("\nTop 15 Cities in Neon DB now:", flush=True)
        city_rows = db.execute(
            select(Job.city, func.count(Job.id))
            .where(Job.is_active == True, Job.city != None)
            .group_by(Job.city)
            .order_by(desc(func.count(Job.id)))
        ).all()
        for c, count in city_rows[:15]:
            print(f"  {c}: {count}", flush=True)
    finally:
        db.close()

if __name__ == "__main__":
    harvest_india_ats()
