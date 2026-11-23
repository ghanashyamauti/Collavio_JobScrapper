import json
import logging
import httpx
from typing import List, Optional, Any, Dict
from datetime import datetime
from bs4 import BeautifulSoup
from app.collectors.base import BaseCollector, RawJob
from app.config import settings

logger = logging.getLogger(__name__)


class JSONLDCollector(BaseCollector):
    name: str = "jsonld"

    def __init__(self, career_urls: Optional[List[str]] = None):
        if career_urls:
            self.urls = career_urls
        else:
            self.urls = [u.strip() for u in settings.CAREER_URLS.split(",") if u.strip()]

    def _extract_job_postings(self, data: Any) -> List[Dict[str, Any]]:
        postings = []
        if isinstance(data, list):
            for item in data:
                postings.extend(self._extract_job_postings(item))
        elif isinstance(data, dict):
            item_type = data.get("@type")
            if item_type == "JobPosting" or (isinstance(item_type, list) and "JobPosting" in item_type):
                postings.append(data)
            if "@graph" in data and isinstance(data["@graph"], list):
                postings.extend(self._extract_job_postings(data["@graph"]))
        return postings

    def collect(self) -> List[RawJob]:
        """Scrapes configured career URLs and parses Schema.org JobPosting JSON-LD blocks."""
        if not self.urls:
            logger.info("[JSON-LD] No custom CAREER_URLS configured, skipping.")
            return []

        jobs: List[RawJob] = []
        headers = {
            "User-Agent": "JobPulse/1.0 (+https://github.com/jobpulse/aggregator)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            for target_url in self.urls:
                try:
                    resp = client.get(target_url)
                    if resp.status_code != 200:
                        logger.debug(f"[JSON-LD] HTTP {resp.status_code} for {target_url}")
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    scripts = soup.find_all("script", type=lambda t: t and "ld+json" in t.lower())

                    for script in scripts:
                        if not script.string:
                            continue
                        try:
                            payload = json.loads(script.string.strip())
                            extracted = self._extract_job_postings(payload)

                            for item in extracted:
                                title = (item.get("title") or "").strip()
                                org = item.get("hiringOrganization") or {}
                                company = org.get("name") if isinstance(org, dict) else str(org)
                                company = (company or "Unknown").strip()
                                apply_url = item.get("url") or target_url

                                if not title:
                                    continue

                                # Location parsing
                                loc_data = item.get("jobLocation")
                                location_name = ""
                                if isinstance(loc_data, dict):
                                    addr = loc_data.get("address")
                                    if isinstance(addr, dict):
                                        parts = [
                                            addr.get("addressLocality"),
                                            addr.get("addressRegion"),
                                            addr.get("addressCountry"),
                                        ]
                                        location_name = ", ".join([p for p in parts if p])
                                    elif isinstance(addr, str):
                                        location_name = addr
                                elif isinstance(loc_data, list):
                                    loc_parts = []
                                    for l in loc_data:
                                        if isinstance(l, dict) and "address" in l:
                                            addr = l["address"]
                                            if isinstance(addr, dict):
                                                loc_parts.append(addr.get("addressLocality") or "")
                                    location_name = ", ".join([p for p in loc_parts if p])

                                job_loc_type = str(item.get("jobLocationType") or "").lower()
                                is_remote = (
                                    "telecommute" in job_loc_type
                                    or "remote" in location_name.lower()
                                    or "remote" in title.lower()
                                )

                                # Salary parsing
                                base_sal = item.get("baseSalary") or {}
                                salary_min = None
                                salary_max = None
                                currency = None
                                if isinstance(base_sal, dict):
                                    currency = base_sal.get("currency")
                                    val = base_sal.get("value")
                                    if isinstance(val, dict):
                                        salary_min = val.get("minValue")
                                        salary_max = val.get("maxValue") or val.get("value")
                                    elif isinstance(val, (int, float)):
                                        salary_min = float(val)

                                desc = item.get("description") or ""

                                posted_at = None
                                date_posted = item.get("datePosted")
                                if date_posted:
                                    try:
                                        posted_at = datetime.fromisoformat(str(date_posted).replace("Z", "+00:00"))
                                    except Exception:
                                        pass

                                jobs.append(
                                    RawJob(
                                        source_name="jsonld",
                                        external_id=item.get("identifier", {}).get("value") if isinstance(item.get("identifier"), dict) else None,
                                        title=title,
                                        company=company,
                                        apply_url=apply_url,
                                        location=location_name or ("Remote" if is_remote else "Unspecified"),
                                        is_remote=is_remote,
                                        job_type=item.get("employmentType"),
                                        salary_min=float(salary_min) if salary_min is not None else None,
                                        salary_max=float(salary_max) if salary_max is not None else None,
                                        currency=currency,
                                        description=desc,
                                        posted_at=posted_at,
                                    )
                                )
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    logger.warning(f"[JSON-LD] Error crawling {target_url}: {e}")

        logger.info(f"[JSON-LD] Total jobs collected: {len(jobs)}")
        return jobs
