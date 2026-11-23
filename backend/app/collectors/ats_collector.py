import logging
import httpx
from typing import List, Optional
from datetime import datetime
from app.collectors.base import BaseCollector, RawJob
from app.config import settings

logger = logging.getLogger(__name__)


class ATSCollector(BaseCollector):
    name: str = "ats_direct"

    def __init__(self):
        self.greenhouse_boards = [
            b.strip() for b in settings.GREENHOUSE_BOARDS.split(",") if b.strip()
        ]
        self.lever_boards = [
            b.strip() for b in settings.LEVER_BOARDS.split(",") if b.strip()
        ]
        self.ashby_boards = [
            b.strip() for b in settings.ASHBY_BOARDS.split(",") if b.strip()
        ]
        self.smartrecruiters_boards = [
            b.strip() for b in settings.SMARTRECRUITERS_BOARDS.split(",") if b.strip()
        ]
        self.workable_boards = [
            b.strip() for b in settings.WORKABLE_BOARDS.split(",") if b.strip()
        ]

    def collect(self) -> List[RawJob]:
        """Harvests public job postings across configured ATS endpoints."""
        all_jobs: List[RawJob] = []

        headers = {
            "User-Agent": "JobPulse/1.0 (+https://github.com/jobpulse/aggregator)",
            "Accept": "application/json",
        }

        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            # 1. Greenhouse
            for slug in self.greenhouse_boards:
                try:
                    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        company_name = slug.capitalize()
                        for item in data.get("jobs", []):
                            job_id = str(item.get("id"))
                            title = (item.get("title") or "").strip()
                            apply_url = item.get("absolute_url")
                            if not title or not apply_url:
                                continue

                            location_dict = item.get("location") or {}
                            loc_name = location_dict.get("name") if isinstance(location_dict, dict) else str(location_dict)
                            desc = item.get("content") or ""

                            posted_at = None
                            raw_date = item.get("updated_at")
                            if raw_date:
                                try:
                                    posted_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                                except Exception:
                                    pass

                            all_jobs.append(
                                RawJob(
                                    source_name="greenhouse",
                                    external_id=f"gh_{slug}_{job_id}",
                                    title=title,
                                    company=company_name,
                                    apply_url=apply_url,
                                    location=loc_name,
                                    is_remote="remote" in (loc_name or "").lower(),
                                    description=desc,
                                    posted_at=posted_at,
                                )
                            )
                        logger.info(f"[ATS] Greenhouse '{slug}' fetched successfully.")
                    else:
                        logger.debug(f"[ATS] Greenhouse '{slug}' responded with status {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[ATS] Greenhouse '{slug}' error: {e}")

            # 2. Lever
            for slug in self.lever_boards:
                try:
                    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        company_name = slug.capitalize()
                        if isinstance(data, list):
                            for item in data:
                                job_id = str(item.get("id"))
                                title = (item.get("text") or "").strip()
                                apply_url = item.get("hostedUrl") or item.get("applyUrl")
                                if not title or not apply_url:
                                    continue

                                categories = item.get("categories") or {}
                                loc_name = categories.get("location") or ""
                                commitment = categories.get("commitment")
                                desc = item.get("descriptionPlain") or item.get("description") or ""

                                posted_at = None
                                created_ts = item.get("createdAt")
                                if created_ts:
                                    try:
                                        posted_at = datetime.fromtimestamp(created_ts / 1000.0)
                                    except Exception:
                                        pass

                                all_jobs.append(
                                    RawJob(
                                        source_name="lever",
                                        external_id=f"lever_{slug}_{job_id}",
                                        title=title,
                                        company=company_name,
                                        apply_url=apply_url,
                                        location=loc_name,
                                        is_remote="remote" in (loc_name or "").lower() or (item.get("workplaceType") == "remote"),
                                        job_type=commitment,
                                        description=desc,
                                        posted_at=posted_at,
                                    )
                                )
                        logger.info(f"[ATS] Lever '{slug}' fetched successfully.")
                    else:
                        logger.debug(f"[ATS] Lever '{slug}' responded with status {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[ATS] Lever '{slug}' error: {e}")

            # 3. Ashby
            for slug in self.ashby_boards:
                try:
                    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        company_name = slug.capitalize()
                        for item in data.get("jobs", []):
                            job_id = str(item.get("id"))
                            title = (item.get("title") or "").strip()
                            apply_url = item.get("jobUrl")
                            if not title or not apply_url:
                                continue

                            location = item.get("location") or ""
                            is_remote = bool(item.get("isRemote")) or ("remote" in location.lower())
                            employment_type = item.get("employmentType")
                            desc = item.get("descriptionHtml") or ""

                            salary_min = None
                            salary_max = None
                            currency = None
                            comp = item.get("compensation") or {}
                            if isinstance(comp, dict):
                                tiers = comp.get("compensationTiers")
                                if tiers and isinstance(tiers, list) and len(tiers) > 0:
                                    tier = tiers[0]
                                    salary_min = tier.get("minSalary")
                                    salary_max = tier.get("maxSalary")
                                    currency = tier.get("currency")

                            posted_at = None
                            pub = item.get("publishedAt")
                            if pub:
                                try:
                                    posted_at = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                                except Exception:
                                    pass

                            all_jobs.append(
                                RawJob(
                                    source_name="ashby",
                                    external_id=f"ashby_{slug}_{job_id}",
                                    title=title,
                                    company=company_name,
                                    apply_url=apply_url,
                                    location=location,
                                    is_remote=is_remote,
                                    job_type=employment_type,
                                    salary_min=salary_min,
                                    salary_max=salary_max,
                                    currency=currency,
                                    description=desc,
                                    posted_at=posted_at,
                                )
                            )
                        logger.info(f"[ATS] Ashby '{slug}' fetched successfully.")
                    else:
                        logger.debug(f"[ATS] Ashby '{slug}' responded with status {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[ATS] Ashby '{slug}' error: {e}")

            # 4. SmartRecruiters
            for slug in self.smartrecruiters_boards:
                try:
                    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=40"
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        company_name = slug.capitalize()
                        for item in data.get("content", []):
                            job_id = str(item.get("id"))
                            title = (item.get("name") or "").strip()
                            apply_url = f"https://jobs.smartrecruiters.com/{slug}/{job_id}"
                            if not title:
                                continue

                            loc_dict = item.get("location") or {}
                            city = loc_dict.get("city") or ""
                            country = loc_dict.get("country") or ""
                            location_str = f"{city}, {country}".strip(", ")
                            is_remote = bool(loc_dict.get("remote")) or "remote" in location_str.lower()

                            emp_type_dict = item.get("typeOfEmployment") or {}
                            job_type = emp_type_dict.get("label") if isinstance(emp_type_dict, dict) else None

                            posted_at = None
                            rel_date = item.get("releasedDate")
                            if rel_date:
                                try:
                                    posted_at = datetime.fromisoformat(rel_date.replace("Z", "+00:00"))
                                except Exception:
                                    pass

                            all_jobs.append(
                                RawJob(
                                    source_name="smartrecruiters",
                                    external_id=f"sr_{slug}_{job_id}",
                                    title=title,
                                    company=company_name,
                                    apply_url=apply_url,
                                    location=location_str,
                                    city=city or None,
                                    is_remote=is_remote,
                                    job_type=job_type,
                                    posted_at=posted_at,
                                )
                            )
                        logger.info(f"[ATS] SmartRecruiters '{slug}' fetched successfully.")
                    else:
                        logger.debug(f"[ATS] SmartRecruiters '{slug}' responded with status {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[ATS] SmartRecruiters '{slug}' error: {e}")

            # 5. Workable
            for slug in self.workable_boards:
                try:
                    url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true"
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        company_name = slug.capitalize()
                        for item in data.get("jobs", []):
                            shortcode = str(item.get("shortcode") or item.get("id"))
                            title = (item.get("title") or "").strip()
                            apply_url = item.get("url") or item.get("application_url")
                            if not title or not apply_url:
                                continue

                            city = item.get("city") or ""
                            country = item.get("country") or ""
                            loc_str = f"{city}, {country}".strip(", ")
                            is_remote = bool(item.get("telecommuting")) or "remote" in loc_str.lower()

                            posted_at = None
                            pub_date = item.get("published_on")
                            if pub_date:
                                try:
                                    posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                                except Exception:
                                    pass

                            all_jobs.append(
                                RawJob(
                                    source_name="workable",
                                    external_id=f"workable_{slug}_{shortcode}",
                                    title=title,
                                    company=company_name,
                                    apply_url=apply_url,
                                    location=loc_str,
                                    city=city or None,
                                    is_remote=is_remote,
                                    description=item.get("description"),
                                    posted_at=posted_at,
                                )
                            )
                        logger.info(f"[ATS] Workable '{slug}' fetched successfully.")
                except Exception as e:
                    logger.warning(f"[ATS] Workable '{slug}' error: {e}")

        logger.info(f"[ATS] Total jobs collected across direct ATS boards: {len(all_jobs)}")
        return all_jobs
