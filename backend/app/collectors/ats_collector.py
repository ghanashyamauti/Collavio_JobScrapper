import os
import json
import logging
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import concurrent.futures

from app.collectors.base import BaseCollector, RawJob
from app.config import settings

logger = logging.getLogger("ats_collector")


class ATSCollector(BaseCollector):
    name: str = "ats_direct"

    def __init__(
        self,
        greenhouse_boards: Optional[List[str]] = None,
        lever_boards: Optional[List[str]] = None,
        ashby_boards: Optional[List[str]] = None,
        smartrecruiters_boards: Optional[List[str]] = None,
    ):
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        ats_file = os.path.join(data_dir, "ats_companies.json")

        json_gh, json_lever, json_ashby, json_smart = [], [], [], []
        if os.path.exists(ats_file):
            try:
                with open(ats_file, "r", encoding="utf-8") as f:
                    catalogs = json.load(f)
                    json_gh = catalogs.get("greenhouse", [])
                    json_lever = catalogs.get("lever", [])
                    json_ashby = catalogs.get("ashby", [])
                    json_smart = catalogs.get("smartrecruiters", [])
            except Exception as e:
                logger.warning(f"Failed to read ats_companies.json: {e}")

        env_gh = [b.strip() for b in settings.GREENHOUSE_BOARDS.split(",") if b.strip()]
        self.greenhouse_boards = greenhouse_boards or list(dict.fromkeys(env_gh + json_gh))

        env_lever = [b.strip() for b in settings.LEVER_BOARDS.split(",") if b.strip()]
        self.lever_boards = lever_boards or list(dict.fromkeys(env_lever + json_lever))

        env_ashby = [b.strip() for b in settings.ASHBY_BOARDS.split(",") if b.strip()]
        self.ashby_boards = ashby_boards or list(dict.fromkeys(env_ashby + json_ashby))

        env_smart = [b.strip() for b in settings.SMARTRECRUITERS_BOARDS.split(",") if b.strip()]
        self.smartrecruiters_boards = smartrecruiters_boards or list(dict.fromkeys(env_smart + json_smart))

    async def _fetch_greenhouse_board(self, client: httpx.AsyncClient, sem: asyncio.Semaphore, slug: str) -> List[RawJob]:
        """Fetches lightweight list-only Greenhouse board without heavy ?content=true."""
        async with sem:
            url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs_data = data.get("jobs", [])
                    company_name = slug.replace("-", " ").capitalize()
                    out = []
                    for item in jobs_data:
                        title = (item.get("title") or "").strip()
                        apply_url = item.get("absolute_url")
                        job_id = str(item.get("id"))
                        if not title or not apply_url:
                            continue
                        loc_obj = item.get("location") or {}
                        location = loc_obj.get("name", "Remote") if isinstance(loc_obj, dict) else str(loc_obj)
                        out.append(RawJob(
                            title=title,
                            company=company_name,
                            location=location,
                            apply_url=apply_url,
                            external_id=f"gh_{job_id}",
                            source_name="greenhouse",
                            description=None,  # Lightweight: on-demand detail fetch
                        ))
                    return out
            except Exception:
                pass
            return []

    async def _fetch_lever_board(self, client: httpx.AsyncClient, sem: asyncio.Semaphore, slug: str) -> List[RawJob]:
        """Fetches Lever postings with pagination support."""
        async with sem:
            out = []
            company_name = slug.replace("-", " ").capitalize()
            limit = 100
            skip = 0

            while True:
                url = f"https://api.lever.co/v0/postings/{slug}?mode=json&limit={limit}&skip={skip}"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break
                    items = resp.json()
                    if not isinstance(items, list) or len(items) == 0:
                        break

                    for item in items:
                        title = (item.get("text") or "").strip()
                        apply_url = item.get("hostedUrl") or item.get("applyUrl")
                        job_id = str(item.get("id"))
                        if not title or not apply_url:
                            continue
                        categories = item.get("categories") or {}
                        location = categories.get("location") or "Remote"
                        team = categories.get("team")
                        job_type = categories.get("commitment")

                        out.append(RawJob(
                            title=title,
                            company=company_name,
                            location=location,
                            apply_url=apply_url,
                            external_id=f"lever_{job_id}",
                            source_name="lever",
                            job_type=job_type,
                            description=None,
                        ))

                    if len(items) < limit:
                        break
                    skip += limit
                    if skip >= 500:  # Cap per board to prevent infinite loops
                        break
                except Exception:
                    break
            return out

    async def _fetch_ashby_board(self, client: httpx.AsyncClient, sem: asyncio.Semaphore, slug: str) -> List[RawJob]:
        """Fetches Ashby postings via public posting-api."""
        async with sem:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs_data = data.get("jobs", [])
                    company_name = slug.replace("-", " ").capitalize()
                    out = []
                    for item in jobs_data:
                        title = (item.get("title") or "").strip()
                        apply_url = item.get("jobUrl") or item.get("applyUrl")
                        job_id = str(item.get("id"))
                        if not title or not apply_url:
                            continue
                        location = item.get("location") or "Remote"
                        job_type = item.get("employmentType")
                        is_remote = bool(item.get("isRemote"))

                        salary_min = None
                        salary_max = None
                        currency = None
                        comp = item.get("compensation") or {}
                        if isinstance(comp, dict):
                            summary = comp.get("compensationSummary")
                            currency = comp.get("currency")
                            val = comp.get("value") or {}
                            if isinstance(val, dict):
                                salary_min = val.get("minValue")
                                salary_max = val.get("maxValue")

                        out.append(RawJob(
                            title=title,
                            company=company_name,
                            location=location,
                            apply_url=apply_url,
                            external_id=f"ashby_{job_id}",
                            source_name="ashby",
                            job_type=job_type,
                            is_remote=is_remote,
                            salary_min=float(salary_min) if salary_min else None,
                            salary_max=float(salary_max) if salary_max else None,
                            currency=currency,
                            description=None,
                        ))
                    return out
            except Exception:
                pass
            return []

    async def _fetch_smartrecruiters_board(self, client: httpx.AsyncClient, sem: asyncio.Semaphore, slug: str) -> List[RawJob]:
        """Fetches SmartRecruiters postings via public postings API."""
        async with sem:
            url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("content", [])
                    company_name = slug.replace("-", " ").capitalize()
                    out = []
                    for item in content:
                        title = (item.get("name") or "").strip()
                        job_id = str(item.get("id"))
                        if not title or not job_id:
                            continue
                        apply_url = f"https://jobs.smartrecruiters.com/{slug}/{job_id}"
                        loc = item.get("location") or {}
                        city = loc.get("city") or ""
                        country = loc.get("country") or ""
                        location = f"{city}, {country}".strip(", ") or "Remote"

                        out.append(RawJob(
                            title=title,
                            company=company_name,
                            location=location,
                            apply_url=apply_url,
                            external_id=f"sr_{job_id}",
                            source_name="smartrecruiters",
                            description=None,
                        ))
                    return out
            except Exception:
                pass
            return []

    async def collect_async(self) -> List[RawJob]:
        """Concurrently harvests all 2,500+ ATS boards using asyncio.Semaphore(50)."""
        sem = asyncio.Semaphore(50)
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
        timeout = httpx.Timeout(10.0, connect=8.0)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        logger.info(
            f"[ATS] Starting async harvest across {len(self.greenhouse_boards)} Greenhouse, "
            f"{len(self.lever_boards)} Lever, {len(self.ashby_boards)} Ashby, "
            f"{len(self.smartrecruiters_boards)} SmartRecruiters endpoints..."
        )

        async with httpx.AsyncClient(limits=limits, timeout=timeout, headers=headers, follow_redirects=True) as client:
            tasks = []

            for slug in self.greenhouse_boards:
                tasks.append(self._fetch_greenhouse_board(client, sem, slug))
            for slug in self.lever_boards:
                tasks.append(self._fetch_lever_board(client, sem, slug))
            for slug in self.ashby_boards:
                tasks.append(self._fetch_ashby_board(client, sem, slug))
            for slug in self.smartrecruiters_boards:
                tasks.append(self._fetch_smartrecruiters_board(client, sem, slug))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: List[RawJob] = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

        logger.info(f"[ATS] Total jobs collected across 2,500+ direct ATS boards: {len(all_jobs)}")
        return all_jobs

    def collect(self) -> List[RawJob]:
        """Synchronous wrapper for BaseCollector interface."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, self.collect_async()).result()
        else:
            return asyncio.run(self.collect_async())
