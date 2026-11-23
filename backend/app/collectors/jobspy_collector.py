import time
import logging
from typing import List, Optional
from datetime import datetime
from app.collectors.base import BaseCollector, RawJob
from app.config import settings

logger = logging.getLogger(__name__)


class JobSpyCollector(BaseCollector):
    name: str = "jobspy"

    def __init__(
        self,
        sites: Optional[List[str]] = None,
        queries: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        results_per_query: Optional[int] = None,
        hours_old: Optional[int] = None,
    ):
        raw_sites = sites or [s.strip() for s in settings.JOBSPY_SITES.split(",") if s.strip()]
        self.sites = raw_sites or ["linkedin", "naukri", "indeed", "glassdoor"]
        self.queries = queries or [q.strip() for q in settings.SEARCH_QUERIES.split(",") if q.strip()]
        self.locations = locations or [l.strip() for l in settings.SEARCH_LOCATIONS.split(",") if l.strip()]
        self.results_per_query = results_per_query or settings.RESULTS_PER_QUERY
        self.hours_old = hours_old or settings.HOURS_OLD
        self.country_indeed = settings.COUNTRY_INDEED
        self.proxies = [p.strip() for p in settings.PROXIES.split(",")] if settings.PROXIES else None

    def collect(self, max_queries: int = 4) -> List[RawJob]:
        """
        Runs JobSpy across configured search queries, locations, and job boards.
        Uses rate-limiting and robust exception handling per query batch.
        """
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy is not installed or failed to import.")
            return []

        jobs: List[RawJob] = []
        # Limit combinations per batch run to avoid 429 rate limiting
        queries_to_run = self.queries[:max_queries]
        locations_to_run = self.locations[:2]  # primary top locations

        for query in queries_to_run:
            for location in locations_to_run:
                logger.info(f"[JobSpy] Scraping query='{query}', location='{location}' on {self.sites}...")
                try:
                    df = scrape_jobs(
                        site_name=self.sites,
                        search_term=query,
                        location=location,
                        results_wanted=min(self.results_per_query, 15),
                        hours_old=self.hours_old,
                        country_indeed=self.country_indeed,
                        proxies=self.proxies,
                        is_remote=("remote" in location.lower()),
                    )

                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            title = str(row.get("title") or "").strip()
                            company = str(row.get("company") or "").strip()
                            apply_url = str(row.get("job_url") or row.get("job_url_direct") or "").strip()
                            if not title or not company or not apply_url:
                                continue

                            site_name = str(row.get("site") or "jobspy").lower().strip()
                            ext_id = str(row.get("id") or "").strip() or None
                            job_location = str(row.get("location") or location).strip()
                            desc = str(row.get("description") or "").strip()
                            job_type = str(row.get("job_type") or "").strip() or None

                            salary_min = None
                            salary_max = None
                            try:
                                if row.get("min_amount") is not None and str(row.get("min_amount")) != "nan":
                                    salary_min = float(row.get("min_amount"))
                                if row.get("max_amount") is not None and str(row.get("max_amount")) != "nan":
                                    salary_max = float(row.get("max_amount"))
                            except (ValueError, TypeError):
                                pass

                            currency = str(row.get("currency") or "").strip() or None

                            posted_at = None
                            date_posted = row.get("date_posted")
                            if date_posted and str(date_posted) != "NaT" and str(date_posted) != "nan":
                                if isinstance(date_posted, datetime):
                                    posted_at = date_posted
                                else:
                                    try:
                                        posted_at = datetime.fromisoformat(str(date_posted))
                                    except Exception:
                                        pass

                            jobs.append(
                                RawJob(
                                    source_name=site_name,
                                    external_id=ext_id,
                                    title=title,
                                    company=company,
                                    apply_url=apply_url,
                                    location=job_location,
                                    is_remote="remote" in job_location.lower() or "remote" in location.lower(),
                                    job_type=job_type,
                                    salary_min=salary_min,
                                    salary_max=salary_max,
                                    currency=currency,
                                    description=desc,
                                    posted_at=posted_at,
                                )
                            )

                    time.sleep(1.5)  # Polite pause between queries
                except Exception as e:
                    logger.warning(f"[JobSpy] Batch failed for query '{query}' in '{location}': {e}")
                    time.sleep(1.5)

        logger.info(f"[JobSpy] Total jobs collected: {len(jobs)}")
        return jobs
