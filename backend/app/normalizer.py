import re
import html
import hashlib
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from bs4 import BeautifulSoup


TRACKING_PARAMS = {
    "ref",
    "refid",
    "trk",
    "fbclid",
    "gclid",
    "gh_src",
    "lever-source",
    "source",
    "src",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}

COMPANY_SUFFIX_REGEX = re.compile(
    r"\b(pvt\.?\s*ltd\.?|private\s+limited|limited|ltd\.?|inc\.?|llc\.?|corp\.?|corporation|technologies|solutions|software|india|services|group|labs|llp|gmbh)\b",
    re.IGNORECASE,
)

CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "new delhi": "Delhi",
    "delhi": "Delhi",
    "delhi ncr": "Delhi NCR",
    "ncr": "Delhi NCR",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "chennai": "Chennai",
    "madras": "Chennai",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "ahmedabad": "Ahmedabad",
    "noida": "Noida",
    "nyc": "New York",
    "new york": "New York",
    "new york city": "New York",
    "sf": "San Francisco",
    "san francisco": "San Francisco",
    "london": "London",
    "berlin": "Berlin",
    "singapore": "Singapore",
    "toronto": "Toronto",
    "remote": "Remote",
}

REMOTE_KEYWORDS = ["remote", "work from home", "wfh", "worldwide", "anywhere", "telecommute"]

CATEGORIES = [
    (
        "Software Development",
        [
            r"software\s*developer",
            r"software\s*engineer",
            r"full[\s-]?stack",
            r"frontend",
            r"front[\s-]?end",
            r"backend",
            r"back[\s-]?end",
            r"web\s*developer",
            r"mobile\s*developer",
            r"ios\s*developer",
            r"android\s*developer",
            r"ios\s*engineer",
            r"android\s*engineer",
            r"\bsde\b",
            r"\bsde[\s-]?\d",
            r"programmer",
            r"\bdeveloper\b",
            r"\bsoftware\b",
            r"application\s*engineer",
            r"applications\s*engineer",
            r"tech\s*lead",
            r"lead\s*engineer",
            r"staff\s*engineer",
            r"principal\s*engineer",
            r"solutions\s*architect",
            r"software\s*architect",
        ],
    ),
    (
        "DevOps & Cloud",
        [
            r"devops",
            r"\bsre\b",
            r"site\s*reliability",
            r"cloud\s*engineer",
            r"platform\s*engineer",
            r"infrastructure\s*engineer",
            r"systems\s*engineer",
            r"kubernetes",
            r"\baws\b",
            r"cloud\s*architect",
            r"infrastructure",
            r"sysadmin",
        ],
    ),
    (
        "Data & AI",
        [
            r"data\s*scientist",
            r"data\s*science",
            r"machine\s*learning",
            r"deep\s*learning",
            r"artificial\s*intelligence",
            r"data\s*engineer",
            r"data\s*analyst",
            r"analytics\s*engineer",
            r"\bml\b",
            r"\bai\b",
            r"\bnlp\b",
            r"computer\s*vision",
            r"big\s*data",
            r"business\s*intelligence",
            r"\bbi\b",
            r"\bdata\b",
        ],
    ),
    (
        "QA & Testing",
        [
            r"qa\s*engineer",
            r"quality\s*assurance",
            r"\bsdet\b",
            r"test\s*engineer",
            r"automation\s*engineer",
            r"test\s*automation",
            r"\bqa\b",
            r"quality\s*engineer",
            r"test\s*lead",
        ],
    ),
    (
        "Cybersecurity",
        [
            r"security\s*engineer",
            r"\binfosec\b",
            r"cybersecurity",
            r"cyber\s*security",
            r"security\s*analyst",
            r"penetration\s*tester",
            r"information\s*security",
            r"soc\s*analyst",
            r"security\s*architect",
        ],
    ),
    (
        "Product Management",
        [
            r"product\s*manager",
            r"product\s*management",
            r"product\s*owner",
            r"\bapm\b",
            r"\bgpm\b",
            r"technical\s*product\s*manager",
            r"\btpm\b",
            r"\bproduct\b",
        ],
    ),
    (
        "UI/UX & Design",
        [
            r"ui[\s/]?ux",
            r"product\s*designer",
            r"ux\s*designer",
            r"ui\s*designer",
            r"graphic\s*designer",
            r"interaction\s*designer",
            r"brand\s*designer",
            r"visual\s*designer",
            r"web\s*designer",
            r"creative\s*director",
            r"figma",
            r"\bdesigner\b",
            r"\bdesign\b",
        ],
    ),
    (
        "Marketing & Content",
        [
            r"marketing",
            r"seo",
            r"sem",
            r"content\s*writer",
            r"copywriter",
            r"growth\s*marketer",
            r"social\s*media",
            r"brand\s*manager",
            r"digital\s*marketing",
            r"email\s*marketing",
            r"demand\s*generation",
            r"public\s*relations",
            r"\bpr\b",
        ],
    ),
    (
        "Sales & Growth",
        [
            r"\bsales\b",
            r"account\s*executive",
            r"\bae\b",
            r"\bbdr\b",
            r"\bsdr\b",
            r"business\s*development",
            r"revenue",
            r"client\s*success",
            r"customer\s*success",
            r"growth\s*lead",
            r"partnerships",
            r"relationship\s*manager",
        ],
    ),
    (
        "Finance & Legal",
        [
            r"finance",
            r"financial",
            r"accountant",
            r"accounting",
            r"auditor",
            r"tax\b",
            r"treasury",
            r"legal",
            r"counsel",
            r"compliance",
            r"contracts",
            r"paralegal",
            r"cfo",
            r"controller",
        ],
    ),
    (
        "HR & Recruiting",
        [
            r"\bhr\b",
            r"human\s*resources",
            r"recruiter",
            r"recruiting",
            r"talent\s*acquisition",
            r"people\s*operations",
            r"people\s*partner",
            r"talent\s*sourcer",
            r"people\s*ops",
            r"compensation\s*&\s*benefits",
        ],
    ),
    (
        "Operations & Support",
        [
            r"operations",
            r"operations\s*manager",
            r"customer\s*support",
            r"customer\s*service",
            r"support\s*engineer",
            r"helpdesk",
            r"office\s*manager",
            r"supply\s*chain",
            r"logistics",
            r"procurement",
            r"admin\s*assistant",
        ],
    ),
    (
        "Engineering (Other)",
        [
            r"engineer",
            r"engineering",
            r"hardware",
            r"electrical",
            r"mechanical",
            r"embedded",
            r"firmware",
        ],
    ),
]


def canonicalize_url(url: Optional[str]) -> str:
    """Strips tracking parameters and URL fragments."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    # Keep non-tracking query parameters
    query_items = parse_qsl(parsed.query, keep_blank_values=False)
    filtered = [
        (k, v)
        for k, v in query_items
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    # Reassemble without fragments
    clean_query = urlencode(filtered)
    clean_path = parsed.path.rstrip("/")
    if not clean_path and not parsed.netloc:
        return url.strip()
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        clean_path,
        "",
        clean_query,
        ""  # fragment removed
    ))


def normalize_company(company: Optional[str]) -> str:
    """Lowercases and cleans company name removing punctuation and corporate suffixes."""
    if not company:
        return ""
    name = company.strip().lower()
    # Strip punctuation
    name = re.sub(r"[^\w\s]", " ", name)
    # Strip common corporate suffixes
    name = COMPANY_SUFFIX_REGEX.sub(" ", name)
    # Normalize multiple whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_title(title: Optional[str]) -> str:
    """Normalizes title for indexing and fuzzy deduplication."""
    if not title:
        return ""
    t = title.strip().lower()
    # Standardize common title abbreviations
    t = re.sub(r"\bsr\.?\b", "senior", t)
    t = re.sub(r"\bjr\.?\b", "junior", t)
    t = re.sub(r"\bdev\b", "developer", t)
    t = re.sub(r"\beng\b", "engineer", t)
    t = re.sub(r"\bmgr\b", "manager", t)
    # Remove emojis or unusual symbols
    t = re.sub(r"[^\w\s\-\+/&#]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_location_and_remote(
    location: Optional[str],
    title: Optional[str] = None
) -> Tuple[str, Optional[str], bool]:
    """
    Standardizes location, city name, and determines remote status.
    Returns (clean_location, standard_city, is_remote).
    """
    loc_str = (location or "").strip()
    title_str = (title or "").strip()
    combined = f"{loc_str} {title_str}".lower()

    # Determine remote status
    is_remote = any(re.search(rf"\b{kw}\b", combined, re.IGNORECASE) for kw in REMOTE_KEYWORDS)

    # City matching
    matched_city = None
    loc_lower = loc_str.lower()
    for alias, standard_name in CITY_ALIASES.items():
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, loc_lower):
            matched_city = standard_name
            break

    if not matched_city and is_remote:
        matched_city = "Remote"

    if not loc_str and is_remote:
        loc_str = "Remote"

    return loc_str or "Remote" if is_remote else (loc_str or "Unspecified"), matched_city, is_remote


INDIA_CITIES = {
    "bengaluru", "bangalore", "mumbai", "delhi", "hyderabad", "pune", "chennai"
}


def detect_country(location: Optional[str], city: Optional[str] = None, is_remote: bool = False) -> str:
    """Classifies job location into standardized country: India, United States, United Kingdom, Germany, Remote, or Global."""
    loc = (location or "").lower()
    c = (city or "").lower()

    if (
        "india" in loc
        or loc.endswith(" in")
        or loc.endswith(", in")
        or ", in," in loc
        or c in INDIA_CITIES
        or any(ic in loc for ic in INDIA_CITIES)
    ):
        return "India"

    if any(us in loc for us in [
        "united states", "usa", "u.s.", "u.s.a", "california", "new york", "texas",
        "washington", "san francisco", "seattle", "austin", "boston", "chicago"
    ]) or c in ["new york", "san francisco", "seattle", "chicago"]:
        return "United States"

    if any(uk in loc for uk in ["united kingdom", "london", "england", "scotland", "uk"]) or c == "london":
        return "United Kingdom"

    if any(de in loc for de in ["germany", "berlin", "munich", "frankfurt", "deutschland"]) or c == "berlin":
        return "Germany"

    if is_remote or "remote" in loc or c == "remote" or "worldwide" in loc or "anywhere" in loc:
        return "Remote / Worldwide"

    return "Global"


def classify_category(title: Optional[str], description: Optional[str] = None) -> str:
    """Classifies a job into Tech or Non-Tech categories based on title and keywords."""
    title_text = (title or "").lower()
    desc_preview = (description or "")[:500].lower()
    combined = f"{title_text} {desc_preview}"

    # First check title explicitly against category patterns
    for cat_name, patterns in CATEGORIES:
        for p in patterns:
            if re.search(p, title_text, re.IGNORECASE):
                return cat_name

    # If title wasn't decisive, check the combined title and description preview
    for cat_name, patterns in CATEGORIES:
        for p in patterns:
            if re.search(p, combined, re.IGNORECASE):
                return cat_name

    return "Other"


def parse_experience(
    title: Optional[str],
    description: Optional[str] = None,
    raw_min: Optional[float] = None,
    raw_max: Optional[float] = None
) -> Tuple[Optional[float], Optional[float]]:
    """
    Extracts min_exp and max_exp in years from structured inputs, description regex, or title seniority.
    """
    if raw_min is not None or raw_max is not None:
        return raw_min, raw_max

    search_text = f"{title or ''} {(description or '')[:1500]}"

    # Regex patterns for ranges: "2-4 yrs", "3 to 5 years", "2 - 5 Years of experience"
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:yrs?|years?)",
        search_text,
        re.IGNORECASE,
    )
    if range_match:
        try:
            return float(range_match.group(1)), float(range_match.group(2))
        except ValueError:
            pass

    # Single bound regex: "5+ years", "minimum 3 years", "at least 4 yrs", "5 yrs of experience"
    min_match = re.search(
        r"(?:minimum|at least|min\.?)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:yrs?|years?)",
        search_text,
        re.IGNORECASE,
    )
    if min_match:
        try:
            val = float(min_match.group(1))
            return val, None
        except ValueError:
            pass

    plus_match = re.search(
        r"(\d+(?:\.\d+)?)\s*\+\s*(?:yrs?|years?)",
        search_text,
        re.IGNORECASE,
    )
    if plus_match:
        try:
            val = float(plus_match.group(1))
            return val, None
        except ValueError:
            pass

    # Seniority fallbacks based on title
    title_lower = (title or "").lower()
    if re.search(r"\b(intern|internship|fresher|trainee|graduate)\b", title_lower):
        return 0.0, 1.0
    if re.search(r"\b(junior|jr\.?|associate|entry[\s-]level|sde[\s-]?1|engineer[\s-]?1)\b", title_lower):
        return 0.0, 2.0
    if re.search(r"\b(mid[\s-]level|sde[\s-]?2|engineer[\s-]?2)\b", title_lower):
        return 2.0, 5.0
    if re.search(r"\b(senior|sr\.?|lead|sde[\s-]?3|principal|staff)\b", title_lower):
        if re.search(r"\b(staff|principal)\b", title_lower):
            return 8.0, 15.0
        return 5.0, 9.0
    if re.search(r"\b(director|vp|head of|chief)\b", title_lower):
        return 10.0, 20.0

    return None, None


def clean_html_description(html_content: Optional[str]) -> str:
    """Converts raw or entity-escaped HTML descriptions into clean, editorial plain text with preserved line breaks and bullet points."""
    if not html_content:
        return ""

    # Unescape HTML entities first (handles &lt;p&gt;, &amp;, &#39;, &quot;, etc.)
    content = html.unescape(html.unescape(html_content.strip()))

    # If it's already plain text without HTML tags
    if "<" not in content and ">" not in content:
        return content.strip()

    try:
        soup = BeautifulSoup(content, "html.parser")

        # Replace <li> with bullet characters
        for li in soup.find_all("li"):
            li_text = li.get_text().strip()
            li.replace_with(f"• {li_text}\n")

        # Replace block tags with newlines
        for block in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "ul", "ol"]):
            block.append("\n\n")

        for br in soup.find_all("br"):
            br.replace_with("\n")

        text = soup.get_text()

        # Clean multiple blank lines while preserving paragraph breaks
        cleaned_lines = []
        for line in text.splitlines():
            cleaned_line = line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
            else:
                if cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")

        result = "\n".join(cleaned_lines).strip()
        # Collapse excessive newlines (> 2)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result or content.strip()
    except Exception:
        # Fallback to regex strip if parser fails
        clean = re.sub(r"<[^>]+>", " ", content)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean


def generate_fingerprint(normalized_company: str, normalized_title: str, city: Optional[str]) -> str:
    """Generates sha256 fingerprint from norm_company | norm_title | city.lower()."""
    city_str = (city or "unspecified").strip().lower()
    raw = f"{normalized_company}|{normalized_title}|{city_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
