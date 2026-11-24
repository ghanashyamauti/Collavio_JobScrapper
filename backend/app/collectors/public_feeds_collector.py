import logging
import httpx
import feedparser
from typing import List, Optional
from datetime import datetime
from app.collectors.base import BaseCollector, RawJob
from app.config import settings

logger = logging.getLogger(__name__)


class PublicFeedsCollector(BaseCollector):
    name: str = "public_feeds"

    def __init__(self):
        self.himalayas_key = settings.HIMALAYAS_API_KEY

    def collect(self) -> List[RawJob]:
        """Harvests public JSON and RSS job feeds with zero/free credentials."""
        jobs: List[RawJob] = []

        headers = {
            "User-Agent": "JobPulse/1.0 (+https://github.com/jobpulse/aggregator)",
            "Accept": "application/json",
        }

        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            # 1. Himalayas API
            try:
                him_headers = dict(headers)
                if self.himalayas_key:
                    him_headers["Authorization"] = f"Bearer {self.himalayas_key}"

                cursor = None
                for _ in range(2):  # Fetch 2 pages
                    query_url = "https://himalayas.app/jobs/api?limit=20"
                    if cursor:
                        query_url += f"&cursor={cursor}"
                    resp = client.get(query_url, headers=him_headers)
                    if resp.status_code == 200:
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
                            seniority = item.get("seniority")
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
                    else:
                        break
                logger.info(f"[PublicFeeds] Himalayas fetched: {len(jobs)} jobs so far.")
            except Exception as e:
                logger.warning(f"[PublicFeeds] Himalayas error: {e}")

            # 2. The Muse API (Pages 1-3, Tech & Corporate Non-Tech)
            before_muse = len(jobs)
            try:
                for page_num in range(1, 4):
                    url = f"https://www.themuse.com/api/public/jobs?page={page_num}"
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [])
                        for item in results:
                            title = (item.get("name") or "").strip()
                            comp_dict = item.get("company") or {}
                            company = (comp_dict.get("name") or "").strip()
                            refs = item.get("refs") or {}
                            apply_url = refs.get("landing_page")
                            if not title or not company or not apply_url:
                                continue

                            locations = item.get("locations") or []
                            loc_name = ", ".join([loc.get("name", "") for loc in locations if isinstance(loc, dict)]) or "Unspecified"
                            is_remote = "remote" in loc_name.lower() or any("flexible" in loc.get("name", "").lower() for loc in locations if isinstance(loc, dict))
                            desc = item.get("contents") or ""

                            posted_at = None
                            pub_date = item.get("publication_date")
                            if pub_date:
                                try:
                                    posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                                except Exception:
                                    pass

                            jobs.append(
                                RawJob(
                                    source_name="themuse",
                                    external_id=f"muse_{item.get('id')}",
                                    title=title,
                                    company=company,
                                    apply_url=apply_url,
                                    location=loc_name,
                                    is_remote=is_remote,
                                    description=desc,
                                    posted_at=posted_at,
                                )
                            )
                    else:
                        break
                logger.info(f"[PublicFeeds] The Muse fetched: {len(jobs) - before_muse} jobs.")
            except Exception as e:
                logger.warning(f"[PublicFeeds] The Muse error: {e}")

            # 3. Remotive API
            before_remotive = len(jobs)
            try:
                url = "https://remotive.com/api/remote-jobs?limit=50"
                resp = client.get(url)
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
                logger.info(f"[PublicFeeds] Remotive fetched: {len(jobs) - before_remotive} jobs.")
            except Exception as e:
                logger.warning(f"[PublicFeeds] Remotive error: {e}")

            # 4. Remote OK API
            before_remoteok = len(jobs)
            try:
                url = "https://remoteok.com/api"
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    # Skip index 0 legal object
                    items = data[1:] if isinstance(data, list) and len(data) > 1 else []
                    for item in items[:40]:
                        title = (item.get("position") or "").strip()
                        company = (item.get("company") or "").strip()
                        apply_url = item.get("url")
                        if not title or not company or not apply_url:
                            continue

                        desc = item.get("description") or ""
                        salary_min = item.get("salary_min")
                        salary_max = item.get("salary_max")

                        posted_at = None
                        epoch = item.get("epoch")
                        if epoch:
                            try:
                                posted_at = datetime.fromtimestamp(epoch)
                            except Exception:
                                pass

                        jobs.append(
                            RawJob(
                                source_name="remoteok",
                                external_id=f"remoteok_{item.get('id')}",
                                title=title,
                                company=company,
                                apply_url=apply_url,
                                location=item.get("location") or "Remote",
                                is_remote=True,
                                salary_min=float(salary_min) if salary_min else None,
                                salary_max=float(salary_max) if salary_max else None,
                                currency="USD" if (salary_min or salary_max) else None,
                                description=desc,
                                posted_at=posted_at,
                            )
                        )
                logger.info(f"[PublicFeeds] Remote OK fetched: {len(jobs) - before_remoteok} jobs.")
            except Exception as e:
                logger.warning(f"[PublicFeeds] Remote OK error: {e}")

            # 5. Arbeitnow API (Multi-page bulk harvest)
            before_arbeitnow = len(jobs)
            try:
                for page in range(1, 36):  # Fetch up to 35 pages (~10,500 live jobs)
                    url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_data = data.get("data", [])
                        if not raw_data:
                            break
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
                        if not data.get("links", {}).get("next"):
                            break
                    else:
                        break
                logger.info(f"[PublicFeeds] Arbeitnow fetched: {len(jobs) - before_arbeitnow} jobs across pages.")
            except Exception as e:
                logger.warning(f"[PublicFeeds] Arbeitnow error: {e}")

            # 6. Jobicy API
            before_jobicy = len(jobs)
            try:
                url = "https://jobicy.com/api/v2/remote-jobs?count=40"
                resp = client.get(url)
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
                logger.info(f"[PublicFeeds] Jobicy fetched: {len(jobs) - before_jobicy} jobs.")
            except Exception as e:
                logger.warning(f"[PublicFeeds] Jobicy error: {e}")

        # 7. We Work Remotely RSS (feedparser)
        before_wwr = len(jobs)
        try:
            feed = feedparser.parse("https://weworkremotely.com/remote-jobs.rss")
            for entry in feed.entries:
                raw_title = entry.get("title", "")
                apply_url = entry.get("link")
                if not raw_title or not apply_url:
                    continue

                # Title format typically "Company: Job Title"
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
            logger.info(f"[PublicFeeds] We Work Remotely RSS fetched: {len(jobs) - before_wwr} jobs.")
        except Exception as e:
            logger.warning(f"[PublicFeeds] We Work Remotely RSS error: {e}")

        logger.info(f"[PublicFeeds] Total jobs collected across public feeds: {len(jobs)}")
        return jobs
