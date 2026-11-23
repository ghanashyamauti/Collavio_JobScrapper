import logging
import httpx
from typing import List, Optional
from datetime import datetime
from app.collectors.base import BaseCollector, RawJob
from app.config import settings

logger = logging.getLogger(__name__)


class OptionalAPIsCollector(BaseCollector):
    name: str = "optional_apis"

    def __init__(self):
        self.adzuna_app_id = settings.ADZUNA_APP_ID
        self.adzuna_app_key = settings.ADZUNA_APP_KEY
        self.adzuna_countries = [
            c.strip().lower() for c in settings.ADZUNA_COUNTRIES.split(",") if c.strip()
        ]
        self.jooble_key = settings.JOOBLE_API_KEY
        self.jsearch_key = settings.RAPIDAPI_JSEARCH_KEY

    def collect(self) -> List[RawJob]:
        """Harvests pre-wired optional APIs if their credentials are provided."""
        all_jobs: List[RawJob] = []

        headers = {
            "User-Agent": "JobPulse/1.0 (+https://github.com/jobpulse/aggregator)",
            "Accept": "application/json",
        }

        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            # 1. Adzuna API
            if self.adzuna_app_id and self.adzuna_app_key:
                logger.info("[Adzuna] Credentials detected, querying Adzuna API...")
                for country in self.adzuna_countries:
                    try:
                        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
                        params = {
                            "app_id": self.adzuna_app_id,
                            "app_key": self.adzuna_app_key,
                            "results_per_page": 20,
                            "what": "Developer",
                            "content-type": "application/json",
                        }
                        resp = client.get(url, params=params)
                        if resp.status_code == 200:
                            data = resp.json()
                            results = data.get("results", [])
                            for item in results:
                                title = (item.get("title") or "").strip()
                                comp = item.get("company") or {}
                                company = comp.get("display_name") if isinstance(comp, dict) else str(comp)
                                apply_url = item.get("redirect_url")
                                if not title or not company or not apply_url:
                                    continue

                                loc_dict = item.get("location") or {}
                                loc_name = loc_dict.get("display_name") if isinstance(loc_dict, dict) else ""
                                salary_min = item.get("salary_min")
                                salary_max = item.get("salary_max")
                                desc = item.get("description") or ""

                                posted_at = None
                                created_str = item.get("created")
                                if created_str:
                                    try:
                                        posted_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                                    except Exception:
                                        pass

                                all_jobs.append(
                                    RawJob(
                                        source_name="adzuna",
                                        external_id=str(item.get("id")),
                                        title=title,
                                        company=company,
                                        apply_url=apply_url,
                                        location=loc_name,
                                        is_remote="remote" in (loc_name or "").lower(),
                                        salary_min=float(salary_min) if salary_min else None,
                                        salary_max=float(salary_max) if salary_max else None,
                                        description=desc,
                                        posted_at=posted_at,
                                    )
                                )
                            logger.info(f"[Adzuna] Country '{country}' fetched {len(results)} jobs.")
                        else:
                            logger.warning(f"[Adzuna] Country '{country}' returned HTTP {resp.status_code}")
                    except Exception as e:
                        logger.warning(f"[Adzuna] Error for country '{country}': {e}")
            else:
                logger.info("[Adzuna] ADZUNA_APP_ID/KEY not configured, skipping.")

            # 2. Jooble REST API
            if self.jooble_key:
                logger.info("[Jooble] API key detected, querying Jooble API...")
                try:
                    url = f"https://jooble.org/api/{self.jooble_key}"
                    payload = {"keywords": "Software Engineer", "location": "India", "page": 1}
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        jobs = data.get("jobs", [])
                        for item in jobs:
                            title = (item.get("title") or "").strip()
                            company = (item.get("company") or "").strip()
                            apply_url = item.get("link")
                            if not title or not company or not apply_url:
                                continue

                            location = item.get("location") or ""
                            desc = item.get("snippet") or ""

                            posted_at = None
                            updated = item.get("updated")
                            if updated:
                                try:
                                    posted_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                                except Exception:
                                    pass

                            all_jobs.append(
                                RawJob(
                                    source_name="jooble",
                                    external_id=str(item.get("id")),
                                    title=title,
                                    company=company,
                                    apply_url=apply_url,
                                    location=location,
                                    is_remote="remote" in location.lower(),
                                    description=desc,
                                    posted_at=posted_at,
                                )
                            )
                        logger.info(f"[Jooble] Fetched {len(jobs)} jobs.")
                    else:
                        logger.warning(f"[Jooble] Returned HTTP {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[Jooble] Error: {e}")
            else:
                logger.info("[Jooble] JOOBLE_API_KEY not configured, skipping.")

            # 3. JSearch (Google for Jobs via RapidAPI)
            if self.jsearch_key:
                logger.info("[JSearch] RapidAPI key detected, querying JSearch...")
                try:
                    url = "https://jsearch.p.rapidapi.com/search"
                    params = {"query": "Developer in India", "num_pages": 1, "date_posted": "week"}
                    rap_headers = {
                        "X-RapidAPI-Key": self.jsearch_key,
                        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                    }
                    resp = client.get(url, params=params, headers=rap_headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        data_items = data.get("data", [])
                        for item in data_items:
                            title = (item.get("job_title") or "").strip()
                            company = (item.get("employer_name") or "").strip()
                            apply_url = item.get("job_apply_link")
                            if not title or not company or not apply_url:
                                continue

                            city = item.get("job_city") or ""
                            country = item.get("job_country") or ""
                            loc = f"{city}, {country}".strip(", ")
                            is_remote = bool(item.get("job_is_remote"))
                            desc = item.get("job_description") or ""

                            salary_min = item.get("job_min_salary")
                            salary_max = item.get("job_max_salary")
                            currency = item.get("job_salary_currency")

                            posted_at = None
                            posted_ts = item.get("job_posted_at_timestamp")
                            if posted_ts:
                                try:
                                    posted_at = datetime.fromtimestamp(posted_ts)
                                except Exception:
                                    pass

                            all_jobs.append(
                                RawJob(
                                    source_name="jsearch",
                                    external_id=str(item.get("job_id")),
                                    title=title,
                                    company=company,
                                    apply_url=apply_url,
                                    location=loc,
                                    city=city or None,
                                    is_remote=is_remote,
                                    salary_min=float(salary_min) if salary_min else None,
                                    salary_max=float(salary_max) if salary_max else None,
                                    currency=currency,
                                    description=desc,
                                    posted_at=posted_at,
                                )
                            )
                        logger.info(f"[JSearch] Fetched {len(data_items)} jobs.")
                    else:
                        logger.warning(f"[JSearch] Returned HTTP {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[JSearch] Error: {e}")
            else:
                logger.info("[JSearch] RAPIDAPI_JSEARCH_KEY not configured, skipping.")

        return all_jobs
