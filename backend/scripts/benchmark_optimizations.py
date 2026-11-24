import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import Job, JobSource
from sqlalchemy import text, select, func, or_, and_, desc

def benchmark_optimizations():
    db = SessionLocal()
    print("Testing single-pass combined KPI query...")
    t0 = time.time()
    kpi_sql = text("""
        SELECT 
            count(id) AS total_jobs,
            count(id) FILTER (WHERE is_active = true) AS active_jobs,
            count(id) FILTER (WHERE is_active = true AND country = 'India') AS india_jobs,
            count(id) FILTER (WHERE is_active = true AND is_remote = true) AS remote_jobs,
            count(id) FILTER (WHERE is_saved = true) AS saved_jobs,
            count(id) FILTER (WHERE application_status IN ('applied', 'interview', 'offer')) AS applied_jobs
        FROM jobs;
    """)
    kpi_res = db.execute(kpi_sql).mappings().one()
    t_kpis = time.time() - t0
    print(f"Combined single-pass KPI query took: {t_kpis:.3f}s: {dict(kpi_res)}")

    print("\nTesting fast search (title + company + city + location) for 'software engineer' in Nicaragua...")
    t1 = time.time()
    terms = ["software", "engineer"]
    term_filters = []
    for term in terms:
        w = f"%{term}%"
        term_filters.append(
            or_(
                Job.title.ilike(w),
                Job.company.ilike(w),
                Job.city.ilike(w),
                Job.location.ilike(w),
            )
        )
    q = (
        select(Job)
        .where(
            Job.is_active == True,
            Job.country == "Nicaragua",
            or_(Job.min_exp == None, Job.min_exp <= 2.0),
            or_(Job.max_exp == None, Job.max_exp >= 2.0),
            and_(*term_filters),
        )
        .limit(20)
    )
    jobs = db.execute(q).scalars().all()
    t_search = time.time() - t1
    print(f"Fast get_jobs query took: {t_search:.3f}s (found {len(jobs)} jobs)")

    db.close()

if __name__ == "__main__":
    benchmark_optimizations()
