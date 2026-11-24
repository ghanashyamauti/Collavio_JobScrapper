import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine
from sqlalchemy import text

INDEXES = [
    ("idx_jobs_country_active", "CREATE INDEX IF NOT EXISTS idx_jobs_country_active ON jobs (country) WHERE is_active = true;"),
    ("idx_jobs_city_country", "CREATE INDEX IF NOT EXISTS idx_jobs_city_country ON jobs (country, city) WHERE is_active = true;"),
    ("idx_jobs_title", "CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs (title);"),
    ("idx_jobs_company", "CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs (company);"),
    ("idx_jobs_posted_at_desc", "CREATE INDEX IF NOT EXISTS idx_jobs_posted_at_desc ON jobs (posted_at DESC NULLS LAST);"),
    ("idx_jobs_min_max_exp", "CREATE INDEX IF NOT EXISTS idx_jobs_min_max_exp ON jobs (min_exp, max_exp) WHERE is_active = true;"),
    ("idx_jobs_is_remote_active", "CREATE INDEX IF NOT EXISTS idx_jobs_is_remote_active ON jobs (is_remote) WHERE is_active = true;"),
    ("idx_jobs_category_active", "CREATE INDEX IF NOT EXISTS idx_jobs_category_active ON jobs (category) WHERE is_active = true;"),
]

def add_indexes():
    print("Connecting to database to create performance indexes...")
    with engine.connect() as conn:
        for name, sql in INDEXES:
            t0 = time.time()
            print(f"Creating index {name}...", end=" ", flush=True)
            conn.execute(text(sql))
            conn.commit()
            print(f"Done in {time.time() - t0:.2f}s")
    print("All indexes verified and created successfully!")

if __name__ == "__main__":
    add_indexes()
