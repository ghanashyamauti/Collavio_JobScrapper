import json
import os
import sys
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.collectors.company_catalog import (
    GREENHOUSE_GLOBAL_CATALOG,
    LEVER_GLOBAL_CATALOG,
    ASHBY_GLOBAL_CATALOG,
    SMARTRECRUITERS_GLOBAL_CATALOG,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data")
os.makedirs(DATA_DIR, exist_ok=True)

print("Fetching open-source company catalogs from Riley-Dorrington/job-board-aggregator...")

try:
    gh_raw = httpx.get("https://raw.githubusercontent.com/Riley-Dorrington/job-board-aggregator/main/data/greenhouse_companies.json", timeout=20.0).json()
    print(f"Fetched {len(gh_raw)} Greenhouse companies.")
except Exception as e:
    print(f"Error fetching greenhouse: {e}")
    gh_raw = []

try:
    lever_raw = httpx.get("https://raw.githubusercontent.com/Riley-Dorrington/job-board-aggregator/main/data/lever_companies.json", timeout=20.0).json()
    print(f"Fetched {len(lever_raw)} Lever companies.")
except Exception as e:
    print(f"Error fetching lever: {e}")
    lever_raw = []

try:
    ashby_raw = httpx.get("https://raw.githubusercontent.com/Riley-Dorrington/job-board-aggregator/main/data/ashby_companies.json", timeout=20.0).json()
    print(f"Fetched {len(ashby_raw)} Ashby companies.")
except Exception as e:
    print(f"Error fetching ashby: {e}")
    ashby_raw = []

try:
    wd_raw = httpx.get("https://raw.githubusercontent.com/Riley-Dorrington/job-board-aggregator/main/data/workday_companies.json", timeout=20.0).json()
    print(f"Fetched {len(wd_raw)} Workday companies.")
except Exception as e:
    print(f"Error fetching workday: {e}")
    wd_raw = []

# Merge with our verified priority catalog (Indian MNCs, unicorns, tech giants first)
gh_combined = list(dict.fromkeys(GREENHOUSE_GLOBAL_CATALOG + [str(x).strip().lower() for x in gh_raw if str(x).strip()]))
lever_combined = list(dict.fromkeys(LEVER_GLOBAL_CATALOG + [str(x).strip() for x in lever_raw if str(x).strip()]))
ashby_combined = list(dict.fromkeys(ASHBY_GLOBAL_CATALOG + [str(x).strip().lower() for x in ashby_raw if str(x).strip()]))
smart_combined = list(dict.fromkeys(SMARTRECRUITERS_GLOBAL_CATALOG))

# Curate to top 2,500+ ATS companies
# Take top 1,400 Greenhouse + 700 Lever + 400 Ashby + 100 SmartRecruiters = 2,600 companies!
curated_ats = {
    "greenhouse": gh_combined[:1400],
    "lever": lever_combined[:700],
    "ashby": ashby_combined[:400],
    "smartrecruiters": smart_combined,
}

total_ats = sum(len(v) for v in curated_ats.values())
ats_file = os.path.join(DATA_DIR, "ats_companies.json")
with open(ats_file, "w", encoding="utf-8") as f:
    json.dump(curated_ats, f, indent=2)

print(f"Saved {total_ats} ATS companies to {ats_file}:")
for k, v in curated_ats.items():
    print(f"  - {k}: {len(v)} companies")

# Curate Workday companies
# Filter for well-known enterprises and valid slugs
keywords = [
    "nvidia", "cisco", "dell", "intel", "paypal", "servicenow", "walmart", "boeing",
    "target", "visa", "mastercard", "pwc", "deloitte", "barclays", "accenture", "capgemini",
    "siemens", "ericsson", "hp", "lenovo", "qualcomm", "broadcom", "vmware", "ebay",
    "autodesk", "intuit", "workday", "snowflake", "atlassian", "twilio", "splunk"
]
priority_wd = []
for slug in wd_raw:
    parts = slug.split("|")
    if len(parts) == 3 and any(k in slug.lower() for k in keywords):
        priority_wd.append(slug)

# Also add first 100 general workday tenants
for slug in wd_raw:
    if len(slug.split("|")) == 3 and slug not in priority_wd:
        priority_wd.append(slug)
    if len(priority_wd) >= 120:
        break

wd_file = os.path.join(DATA_DIR, "workday_companies.json")
with open(wd_file, "w", encoding="utf-8") as f:
    json.dump(priority_wd, f, indent=2)

print(f"Saved {len(priority_wd)} Workday companies to {wd_file}.")
