import os
import sys

# Ensure backend is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text

def run_backfill():
    db = SessionLocal()
    try:
        cnt = db.execute(text("SELECT count(*) FROM job_sources WHERE source_name = 'ats_direct'")).scalar()
        print(f"Current ats_direct count: {cnt}")
        
        platforms = [
            ("greenhouse", "%greenhouse.io%"),
            ("lever", "%lever.co%"),
            ("ashby", "%ashbyhq.com%"),
            ("smartrecruiters", "%smartrecruiters.com%"),
            ("workable", "%workable.com%"),
            ("workday", "%myworkdayjobs.com%"),
        ]
        
        for plat, pattern in platforms:
            # 1. Delete rows where job_id already has a row with the target platform
            del_stmt = text("""
                DELETE FROM job_sources 
                WHERE source_name = 'ats_direct' 
                  AND apply_url LIKE :pat
                  AND job_id IN (SELECT job_id FROM job_sources WHERE source_name = :plat)
            """)
            res_del = db.execute(del_stmt, {"pat": pattern, "plat": plat})
            
            # 2. Update remaining ats_direct to real platform
            up_stmt = text("""
                UPDATE job_sources 
                SET source_name = :plat 
                WHERE source_name = 'ats_direct' 
                  AND apply_url LIKE :pat
            """)
            res_up = db.execute(up_stmt, {"pat": pattern, "plat": plat})
            db.commit()
            print(f"  • {plat:15}: deleted {res_del.rowcount} collisions, updated {res_up.rowcount} rows")

        # 3. Handle by external_id prefix if any remain
        by_prefix = [
            ("greenhouse", "gh_%"),
            ("lever", "lever_%"),
            ("ashby", "ashby_%"),
            ("smartrecruiters", "sr_%"),
            ("workday", "wd_%"),
        ]
        for plat, prefix in by_prefix:
            del_stmt = text("""
                DELETE FROM job_sources 
                WHERE source_name = 'ats_direct' 
                  AND external_id LIKE :prefix
                  AND job_id IN (SELECT job_id FROM job_sources WHERE source_name = :plat)
            """)
            res_del = db.execute(del_stmt, {"prefix": prefix, "plat": plat})
            
            up_stmt = text("""
                UPDATE job_sources 
                SET source_name = :plat 
                WHERE source_name = 'ats_direct' 
                  AND external_id LIKE :prefix
            """)
            res_up = db.execute(up_stmt, {"prefix": prefix, "plat": plat})
            db.commit()
            if res_up.rowcount > 0:
                print(f"  • {plat} (by prefix): deleted {res_del.rowcount} collisions, updated {res_up.rowcount} rows")

        # 4. Any lingering ats_direct rows
        rem = db.execute(text("SELECT count(*) FROM job_sources WHERE source_name = 'ats_direct'")).scalar()
        print(f"Lingering ats_direct rows: {rem}")
        if rem > 0:
            db.execute(text("""
                DELETE FROM job_sources 
                WHERE source_name = 'ats_direct'
                  AND job_id IN (SELECT job_id FROM job_sources WHERE source_name = 'greenhouse')
            """))
            db.execute(text("UPDATE job_sources SET source_name = 'greenhouse' WHERE source_name = 'ats_direct'"))
            db.commit()
            print("  • Cleaned and converted lingering rows to greenhouse")

        final_cnt = db.execute(text("SELECT count(*) FROM job_sources WHERE source_name = 'ats_direct'")).scalar()
        print(f"Final ats_direct count: {final_cnt}")

        # Print current source distribution
        print("\n--- NEW ACTIVE JOBS BY SOURCE ---")
        rows = db.execute(text("""
            SELECT s.source_name, count(j.id)
            FROM job_sources s
            JOIN jobs j ON j.id = s.job_id
            WHERE j.is_active = TRUE
            GROUP BY s.source_name
            ORDER BY count(j.id) DESC
        """)).all()
        for sname, scnt in rows:
            print(f"  • {sname:20}: {scnt:,}")

    finally:
        db.close()

if __name__ == "__main__":
    run_backfill()
