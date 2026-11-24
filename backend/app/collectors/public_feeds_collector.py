import logging
import asyncio
import httpx
import feedparser
from typing import List, Optional
from datetime import datetime
import concurrent.futures

from app.collectors.base import BaseCollector, RawJob
from app.config import settings

logger = logging.getLogger("public_feeds_collector")


class PublicFeedsCollector(BaseCollector):
    name: str = "public_feeds"

    def __init__(self):
        self.himalayas_key = settings.HIMALAYAS_API_KEY

    async def _fetch_arbeitnow_page(
        self, client: httpx.AsyncClient, sem: asyncio.Semaphore, page: int
    ) -> List[RawJob]:
        url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        jobs: List[RawJob] = []
        async with sem:
            try:
                resp = await client.get(url, headers=headers, timeout=12.0)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                raw_data = data.get("data", [])
                for item in raw_data:
                    title = (item.get("title") or "").strip()
                    company = (item.get("company_name") or "").strip()
                    apply_url = item.get("url")
                    if not title or not company or not apply_url:
                        continue

                    location = item.get("location") or ""
                    is_remote = bool(item.get("remote")) or "remote" in location.lower()
                    desc = item.get("description") or ""

                    posted_at = None
                    created_ts = item.get("created_at")
                    if created_ts:
                        try:
                            posted_at = datetime.fromtimestamp(created_ts)
                        except Exception:
                            pass

                    jobs.append(
                        RawJob(
                            source_name="arbeitnow",
                            external_id=f"arbeitnow_{item.get('slug')}",
                            title=title,
                            company=company,
                            apply_url=apply_url,
                            location=location,
                            is_remote=is_remote,
                            description=desc,
                            posted_at=posted_at,
                        )
                    )
            except Exception as e:
                logger.debug(f"[Arbeitnow] Page {page} error: {e}")
        return jobs

    async def _fetch_arbeitnow(self, client: httpx.AsyncClient) -> List[RawJob]:
        sem = asyncio.Semaphore(10)
        max_pages = 40  # Deep harvest up to 40 pages (~12,000 live jobs)
        tasks = [self._fetch_arbeitnow_page(client, sem, page) for page in range(1, max_pages + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        jobs: List[RawJob] = []
        for r in results:
            if isinstance(r, list):
                jobs.extend(r)
        logger.info(f"[PublicFeeds] Arbeitnow collected {len(jobs)} jobs across {max_pages} pages.")
        return jobs

    async def _fetch_himalayas(self, client: httpx.AsyncClient) -> List[RawJob]:
        jobs: List[RawJob] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        if self.himalayas_key:
            headers["Authorization"] = f"Bearer {self.himalayas_key}"

        cursor = None
        max_pages = 25  # Walk up to 25 pages (~1,500 remote jobs)
        for _ in range(max_pages):
            query_url = "https://himalayas.app/jobs/api?limit=50"
            if cursor:
                query_url += f"&cursor={cursor}"
            try:
                resp = await client.get(query_url, headers=headers, timeout=12.0)
                if resp.status_code != 200:
                    break
                data = resp.json()
                raw_items = data.get("jobs", [])
                cursor = data.get("nextCursor")
                for item in raw_items:
                    title = (item.get("title") or "").strip()
                    company = (item.get("companyName") or "").strip()
                    apply_url = item.get("applicationLink") or item.get("canonicalUrl")
                    if not title or not company or not apply_url:
                        continue

                    salary_min = item.get("minSalary")
                    salary_max = item.get("maxSalary")
                    currency = item.get("currency")
                    emp_type = item.get("employmentType")
                    desc = item.get("description") or ""

                    posted_at = None
                    pub = item.get("pubDate") or item.get("publishedAt")
                    if pub:
                        try:
                            posted_at = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                        except Exception:
                            pass

                    jobs.append(
                        RawJob(
                            source_name="himalayas",
                            external_id=f"him_{item.get('id') or item.get('slug')}",
                            title=title,
                            company=company,
                            apply_url=apply_url,
                            location="Remote",
                            is_remote=True,
                            job_type=emp_type,
                            salary_min=float(salary_min) if salary_min is not None else None,
                            salary_max=float(salary_max) if salary_max is not None else None,
                            currency=currency,
                            description=desc,
                            posted_at=posted_at,
                        )
                    )
                if not cursor:
                    break
            except Exception as e:
                logger.debug(f"[Himalayas] error: {e}")
                break

        logger.info(f"[PublicFeeds] Himalayas collected {len(jobs)} jobs.")
        return jobs

    async def _fetch_jobicy(self, client: httpx.AsyncClient) -> List[RawJob]:
        jobs: List[RawJob] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        url = "https://jobicy.com/api/v2/remote-jobs?count=50"
        try:
            resp = await client.get(url, headers=headers, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("jobs", []):
                    title = (item.get("jobTitle") or "").strip()
                    company = (item.get("companyName") or "").strip()
                    apply_url = item.get("url")
                    if not title or not company or not apply_url:
                        continue

                    location = item.get("jobGeo") or "Remote"
                    desc = item.get("jobDescription") or item.get("jobExcerpt") or ""
                    job_type = item.get("jobType")

                    salary_min = item.get("annualSalaryMin")
                    salary_max = item.get("annualSalaryMax")
                    currency = item.get("salaryCurrency")

                    posted_at = None
                    pub = item.get("pubDate")
                    if pub:
                        try:
                            posted_at = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    jobs.append(
                        RawJob(
                            source_name="jobicy",
                            external_id=f"jobicy_{item.get('id')}",
                            title=title,
                            company=company,
                            apply_url=apply_url,
                            location=location,
                            is_remote=True,
                            job_type=job_type,
                            salary_min=float(salary_min) if salary_min else None,
                            salary_max=float(salary_max) if salary_max else None,
                            currency=currency,
                            description=desc,
                            posted_at=posted_at,
                        )
                    )
            logger.info(f"[PublicFeeds] Jobicy collected {len(jobs)} jobs.")
        except Exception as e:
            logger.debug(f"[Jobicy] error: {e}")
        return jobs

    async def _fetch_remotive(self, client: httpx.AsyncClient) -> List[RawJob]:
        jobs: List[RawJob] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        url = "https://remotive.com/api/remote-jobs?limit=50"
        try:
            resp = await client.get(url, headers=headers, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("jobs", []):
                    title = (item.get("title") or "").strip()
                    company = (item.get("company_name") or "").strip()
                    apply_url = item.get("url")
                    if not title or not company or not apply_url:
                        continue

                    location = item.get("candidate_required_location") or "Remote"
                    desc = item.get("description") or ""
                    job_type = item.get("job_type")

                    posted_at = None
                    pub = item.get("publication_date")
                    if pub:
                        try:
                            posted_at = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    jobs.append(
                        RawJob(
                            source_name="remotive",
                            external_id=f"remotive_{item.get('id')}",
                            title=title,
                            company=company,
                            apply_url=apply_url,
                            location=location,
                            is_remote=True,
                            job_type=job_type,
                            description=desc,
                            posted_at=posted_at,
                        )
                    )
            logger.info(f"[PublicFeeds] Remotive collected {len(jobs)} jobs.")
        except Exception as e:
            logger.debug(f"[Remotive] error: {e}")
        return jobs

    def _fetch_rss(self) -> List[RawJob]:
        jobs: List[RawJob] = []
        try:
            feed = feedparser.parse("https://weworkremotely.com/remote-jobs.rss")
            for entry in feed.entries:
                raw_title = entry.get("title", "")
                apply_url = entry.get("link")
                if not raw_title or not apply_url:
                    continue

                if ":" in raw_title:
                    company, title = raw_title.split(":", 1)
                    company = company.strip()
                    title = title.strip()
                else:
                    company = "WeWorkRemotely"
                    title = raw_title.strip()

                desc = entry.get("description", "")
                posted_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        posted_at = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                jobs.append(
                    RawJob(
                        source_name="weworkremotely",
                        external_id=f"wwr_{entry.get('id', apply_url)}",
                        title=title,
                        company=company,
                        apply_url=apply_url,
                        location="Remote",
                        is_remote=True,
                        description=desc,
                        posted_at=posted_at,
                    )
                )
            logger.info(f"[PublicFeeds] WeWorkRemotely RSS collected {len(jobs)} jobs.")
        except Exception as e:
            logger.debug(f"[WWR RSS] error: {e}")
        return jobs

    async def collect_async(self) -> List[RawJob]:
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=40)
        async with httpx.AsyncClient(limits=limits, follow_redirects=True) as client:
            tasks = [
                self._fetch_arbeitnow(client),
                self._fetch_himalayas(client),
                self._fetch_jobicy(client),
                self._fetch_remotive(client),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: List[RawJob] = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

        # Sync RSS feeds
        rss_jobs = self._fetch_rss()
        all_jobs.extend(rss_jobs)

        logger.info(f"[PublicFeeds] Total collected: {len(all_jobs)} jobs across feeds.")
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
