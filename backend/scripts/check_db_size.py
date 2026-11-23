import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        db_size_res = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database())), pg_database_size(current_database())")).fetchone()
        jobs_res = conn.execute(text("SELECT pg_size_pretty(pg_total_relation_size('jobs')), count(*) FROM jobs")).fetchone()
        sources_res = conn.execute(text("SELECT pg_size_pretty(pg_total_relation_size('job_sources')), count(*) FROM job_sources")).fetchone()
        runs_res = conn.execute(text("SELECT pg_size_pretty(pg_total_relation_size('scrape_runs')), count(*) FROM scrape_runs")).fetchone()
        
        jobs_breakdown = conn.execute(text("""
            SELECT 
                pg_size_pretty(pg_relation_size('jobs')) AS table_size,
                pg_size_pretty(pg_indexes_size('jobs')) AS index_size,
                pg_size_pretty(pg_total_relation_size('jobs')) AS total_jobs_size
        """)).fetchone()

        total_bytes = db_size_res[1]
        total_mb = total_bytes / (1024 * 1024)
        
        # Neon free tier limit is 512 MB (0.5 GiB)
        neon_limit_mb = 512.0
        free_mb = max(0.0, neon_limit_mb - total_mb)

        print("=== Neon Database Storage Report ===")
        print(f"Total Database Size: {db_size_res[0]} ({total_mb:.2f} MB)")
        print(f"Neon Free Project Limit: {neon_limit_mb:.0f} MB")
        print(f"Available Space on Neon: {free_mb:.2f} MB ({(free_mb / neon_limit_mb) * 100:.1f}% free)")
        print(f"Jobs Table (Data + Indexes): {jobs_res[0]} (Rows: {jobs_res[1]})")
        print(f"  -> Table Data Only: {jobs_breakdown[0]}")
        print(f"  -> Indexes Only: {jobs_breakdown[1]}")
        print(f"Sources Table (Data + Indexes): {sources_res[0]} (Rows: {sources_res[1]})")
        print(f"Scrape Runs Table: {runs_res[0]} (Rows: {runs_res[1]})")
        
        # Calculate per-job cost
        if jobs_res[1] > 0:
            bytes_per_job = (total_bytes) / jobs_res[1]
            print(f"Average Storage per Job: {bytes_per_job / 1024:.2f} KB/job")
            max_jobs_in_free_tier = int((neon_limit_mb * 1024 * 1024) / bytes_per_job)
            print(f"Estimated Max Jobs inside Neon 512 MB limit: ~{max_jobs_in_free_tier:,} jobs")
            needed_for_100k_mb = (100000 * bytes_per_job) / (1024 * 1024)
            print(f"Storage needed for 100,000 jobs: ~{needed_for_100k_mb:.2f} MB ({needed_for_100k_mb / 1024:.2f} GB)")

if __name__ == "__main__":
    main()
