import os
import json
import logging
import asyncio
import httpx
from typing import List, Dict, Any, Optional
import concurrent.futures

from app.collectors.base import BaseCollector, RawJob

logger = logging.getLogger("workday_collector")


class WorkdayCollector(BaseCollector):
    name: str = "workday"

    def __init__(self, tenants: Optional[List[str]] = None):
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        wd_file = os.path.join(data_dir, "workday_companies.json")

        loaded = []
        if os.path.exists(wd_file):
            try:
                with open(wd_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read workday_companies.json: {e}")

        self.tenants = tenants or loaded

    async def _fetch_tenant(self, client: httpx.AsyncClient, sem: asyncio.Semaphore, slug: str) -> List[RawJob]:
        parts = slug.split("|")
        if len(parts) != 3:
            return []

        company, wd, site_id = parts
        wd_num = wd.replace("wd", "")
        base_url = f"https://{company}.wd{wd_num}.myworkdayjobs.com"
        api_url = f"{base_url}/wday/cxs/{company}/{site_id}/jobs"
        company_name = company.replace("-", " ").capitalize()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Origin": base_url,
            "Referer": f"{base_url}/{site_id}",
        }

        out: List[RawJob] = []
        offset = 0
        limit = 20
        max_jobs_per_tenant = 500

        async with sem:
            while offset < max_jobs_per_tenant:
                payload = {
                    "appliedFacets": {},
                    "limit": limit,
                    "offset": offset,
                    "searchText": "",
                }
                try:
                    resp = await client.post(api_url, json=payload, headers=headers, timeout=8.0)
                    if resp.status_code != 200:
                        break
                    try:
                        data = resp.json()
                    except Exception:
                        break
                    postings = data.get("jobPostings", [])
                    if not postings:
                        break

                    for p in postings:
                        title = (p.get("title") or "").strip()
                        ext_path = p.get("externalPath")
                        if not title or not ext_path:
                            continue

                        apply_url = f"{base_url}/en-US/{site_id}{ext_path}"
                        location = p.get("locationsText") or "Remote"
                        bullet_fields = p.get("bulletFields") or []
                        job_type = bullet_fields[0] if bullet_fields else "Full-time"

                        # Extract external job requisition ID from path
                        ext_id = ext_path.strip("/").split("/")[-1]

                        out.append(RawJob(
                            title=title,
                            company=company_name,
                            location=location,
                            apply_url=apply_url,
                            external_id=f"wd_{company}_{ext_id}",
                            source_name="workday",
                            job_type=job_type,
                            description=None,  # Lightweight list-only; detail fetched on-demand
                        ))

                    total = data.get("total", 0)
                    offset += limit
                    if offset >= total:
                        break
                except Exception:
                    break

        return out

    async def collect_async(self) -> List[RawJob]:
        sem = asyncio.Semaphore(25)
        limits = httpx.Limits(max_keepalive_connections=25, max_connections=50)

        logger.info(f"[Workday] Harvesting {len(self.tenants)} verified enterprise Workday career sites...")
        async with httpx.AsyncClient(limits=limits, follow_redirects=True) as client:
            tasks = [self._fetch_tenant(client, sem, slug) for slug in self.tenants]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: List[RawJob] = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

        logger.info(f"[Workday] Total jobs collected across enterprise Workday boards: {len(all_jobs)}")
        return all_jobs

    def collect(self) -> List[RawJob]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, self.collect_async()).result()
        else:
            return asyncio.run(self.collect_async())
