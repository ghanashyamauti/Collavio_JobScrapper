import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine
from sqlalchemy import text

MIGRATION_STEPS = [
    # 1. Trigram extension
    ("pg_trgm extension", "CREATE EXTENSION IF NOT EXISTS pg_trgm;"),
    
    # 2. Search vector column (if not exists)
    ("search_vector column", """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'jobs' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE jobs ADD COLUMN search_vector tsvector;
            END IF;
        END $$;
    """),

    # 3. Populate search_vector
    ("backfill search_vector", """
        UPDATE jobs
        SET search_vector = (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(company, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(city, '') || ' ' || coalesce(location, '')), 'C') ||
            setweight(to_tsvector('english', coalesce(category, '') || ' ' || left(coalesce(description, ''), 2000)), 'D')
        )
        WHERE search_vector IS NULL;
    """),

    # 4. Trigger function for auto-updating search_vector
    ("search_vector trigger func", """
        CREATE OR REPLACE FUNCTION jobs_search_vector_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.company, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.city, '') || ' ' || coalesce(NEW.location, '')), 'C') ||
                setweight(to_tsvector('english', coalesce(NEW.category, '') || ' ' || left(coalesce(NEW.description, ''), 2000)), 'D');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """),

    ("search_vector trigger", """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'tsvectorupdate_jobs'
            ) THEN
                CREATE TRIGGER tsvectorupdate_jobs
                BEFORE INSERT OR UPDATE OF title, company, city, location, category, description
                ON jobs
                FOR EACH ROW EXECUTE FUNCTION jobs_search_vector_trigger();
            END IF;
        END $$;
    """),

    # 5. GIN and composite indexes
    ("idx_jobs_search_vector", "CREATE INDEX IF NOT EXISTS idx_jobs_search_vector ON jobs USING gin (search_vector);"),
    ("idx_jobs_title_trgm", "CREATE INDEX IF NOT EXISTS idx_jobs_title_trgm ON jobs USING gin (title gin_trgm_ops);"),
    ("idx_jobs_company_trgm", "CREATE INDEX IF NOT EXISTS idx_jobs_company_trgm ON jobs USING gin (company gin_trgm_ops);"),
    ("idx_jobs_active_country_city", "CREATE INDEX IF NOT EXISTS idx_jobs_active_country_city ON jobs (is_active, country, city);"),
    ("idx_jobs_active_country_cat", "CREATE INDEX IF NOT EXISTS idx_jobs_active_country_cat ON jobs (is_active, country, category);"),
    ("idx_jobs_active_exp", "CREATE INDEX IF NOT EXISTS idx_jobs_active_exp ON jobs (is_active, min_exp, max_exp);"),
    ("idx_jobs_active_posted", "CREATE INDEX IF NOT EXISTS idx_jobs_active_posted ON jobs (is_active, posted_at DESC NULLS LAST);"),
    ("idx_job_sources_source_job", "CREATE INDEX IF NOT EXISTS idx_job_sources_source_job ON job_sources (source_name, job_id);"),

    # 6. Seniority / Experience Backfill for NULL min_exp/max_exp
    ("backfill intern/fresher", """
        UPDATE jobs
        SET min_exp = 0.0, max_exp = 1.0
        WHERE is_active = true
          AND min_exp IS NULL AND max_exp IS NULL
          AND title ~* '\\m(intern|internship|fresher|trainee|graduate|apprentice)\\M';
    """),

    ("backfill junior/associate/entry/SDE 1", """
        UPDATE jobs
        SET min_exp = 0.0, max_exp = 2.0
        WHERE is_active = true
          AND min_exp IS NULL AND max_exp IS NULL
          AND (
            title ~* '\\m(junior|jr|associate|entry level|sde 1|sde-1|sde i|swe 1|swe-1|swe i|engineer 1|engineer i)\\M'
          );
    """),

    ("backfill mid/SDE 2", """
        UPDATE jobs
        SET min_exp = 2.0, max_exp = 5.0
        WHERE is_active = true
          AND min_exp IS NULL AND max_exp IS NULL
          AND (
            title ~* '\\m(mid-level|mid level|intermediate|sde 2|sde-2|sde ii|swe 2|swe-2|swe ii|engineer 2|engineer ii)\\M'
          );
    """),

    ("backfill senior/lead/SDE 3", """
        UPDATE jobs
        SET min_exp = 5.0, max_exp = 9.0
        WHERE is_active = true
          AND min_exp IS NULL AND max_exp IS NULL
          AND (
            title ~* '\\m(senior|sr|lead|tech lead|team lead|sde 3|sde-3|sde iii|swe 3|swe-3|swe iii|engineer 3|engineer iii)\\M'
          );
    """),

    ("backfill staff/principal/manager/architect/director", """
        UPDATE jobs
        SET min_exp = 8.0, max_exp = 15.0
        WHERE is_active = true
          AND min_exp IS NULL AND max_exp IS NULL
          AND (
            title ~* '\\m(staff|principal|distinguished|architect|manager|director|vp|head of)\\M'
          );
    """),
]

def run_migration():
    print(f"Starting Neon PostgreSQL migration on {engine.url.host}...")
    with engine.connect() as conn:
        for name, sql in MIGRATION_STEPS:
            t0 = time.time()
            print(f"Running step: {name}...", end=" ", flush=True)
            res = conn.execute(text(sql))
            conn.commit()
            rowcount = res.rowcount if hasattr(res, 'rowcount') else -1
            print(f"Done in {time.time() - t0:.2f}s (rowcount: {rowcount})")
    print("Migration and experience backfill completed successfully!")

if __name__ == "__main__":
    run_migration()
