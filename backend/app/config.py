import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Cloud PostgreSQL (Supabase or Neon)
    DATABASE_URL: str = "postgresql+psycopg://USER:PASSWORD@<YOUR_NEON_OR_SUPABASE_URL>:5432/DBNAME?sslmode=require"
    FALLBACK_SQLITE_FOR_LOCAL_DEV: bool = True

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Built-in Scheduler Interval (hours)
    SYNC_INTERVAL_HOURS: int = 6

    # Collector 1: JobSpy
    JOBSPY_SITES: str = "linkedin,naukri,indeed,glassdoor"
    SEARCH_QUERIES: str = "Software Engineer,Product Manager"
    SEARCH_LOCATIONS: str = "Bengaluru,Remote"
    COUNTRY_INDEED: str = "India"
    RESULTS_PER_QUERY: int = 10
    HOURS_OLD: int = 72
    PROXIES: Optional[str] = None

    # Collector 2: Direct Company ATS Slugs
    GREENHOUSE_BOARDS: str = "stripe,gitlab,figma,airbnb,databricks,razorpay,browserstack,postman,phonepe,coinbase"
    LEVER_BOARDS: str = "atlassian,plaid,netflix,spotify,meesho"
    ASHBY_BOARDS: str = "linear,ramp,notion,vercel,openai,elevenlabs"
    SMARTRECRUITERS_BOARDS: str = "visa,bosch,publicissapient,wipro"
    WORKABLE_BOARDS: str = ""

    # Collector 3: Public Feeds
    HIMALAYAS_API_KEY: Optional[str] = None

    # Collector 4: Career URLs for Schema.org JSON-LD
    CAREER_URLS: str = ""

    # Collector 5: Optional APIs
    ADZUNA_APP_ID: Optional[str] = None
    ADZUNA_APP_KEY: Optional[str] = None
    ADZUNA_COUNTRIES: str = "in,us,gb"
    JOOBLE_API_KEY: Optional[str] = None
    RAPIDAPI_JSEARCH_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
