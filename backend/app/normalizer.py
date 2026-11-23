import re
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
        "Data & AI",
        [
            r"\bdata\b",
            r"\bai\b",
            r"\bml\b",
            r"machine learning",
            r"deep learning",
            r"artificial intelligence",
            r"data scientist",
            r"data science",
            r"data engineer",
            r"data analyst",
            r"analytics engineer",
            r"nlp",
            r"computer vision",
            r"big data",
            r"business intelligence",
            r"\bbi\b",
        ],
    ),
    (
        "Product",
        [
            r"\bproduct\b",
            r"product manager",
            r"product management",
            r"product owner",
            r"\bapm\b",
            r"\bgpm\b",
            r"technical product manager",
            r"\btpm\b",
        ],
    ),
    (
        "Design",
        [
            r"ui[\s/]?ux",
            r"product designer",
            r"ux\s*designer",
            r"ui\s*designer",
            r"graphic designer",
            r"interaction designer",
            r"brand designer",
            r"visual designer",
            r"web designer",
            r"creative director",
            r"figma",
        ],
    ),
    (
        "Marketing",
        [
            r"marketing",
            r"seo",
            r"sem",
            r"content writer",
            r"copywriter",
            r"growth marketer",
            r"social media",
            r"brand manager",
            r"digital marketing",
            r"email marketing",
            r"demand generation",
            r"public relations",
            r"\bpr\b",
        ],
    ),
    (
        "Sales & Growth",
        [
            r"\bsales\b",
            r"account executive",
            r"\bae\b",
            r"\bbdr\b",
            r"\bsdr\b",
            r"business development",
            r"revenue",
            r"client success",
            r"customer success",
            r"growth lead",
            r"partnerships",
            r"relationship manager",
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
            r"human resources",
            r"recruiter",
            r"recruiting",
            r"talent acquisition",
            r"people operations",
            r"people partner",
            r"talent sourcer",
            r"people ops",
            r"compensation & benefits",
        ],
    ),
    (
        "Operations & Support",
        [
            r"operations",
            r"operations manager",
            r"customer support",
            r"customer service",
            r"support engineer",
            r"helpdesk",
            r"office manager",
            r"supply chain",
            r"logistics",
            r"procurement",
            r"admin assistant",
        ],
    ),
    (
        "Engineering",
        [
            r"engineer",
            r"engineering",
            r"developer",
            r"software",
            r"frontend",
            r"backend",
            r"full[\s-]?stack",
            r"devops",
            r"\bsre\b",
            r"architect",
            r"mobile developer",
            r"ios",
            r"android",
            r"cloud engineer",
            r"qa engineer",
            r"quality assurance",
            r"sdet",
            r"security engineer",
            r"embedded",
            r"firmware",
            r"systems engineer",
            r"site reliability",
            r"web developer",
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
    """Converts raw HTML descriptions into clean, editorial plain text with preserved line breaks and bullet points."""
    if not html_content:
        return ""

    # If it's already plain text without HTML tags
    if "<" not in html_content and ">" not in html_content:
        return html_content.strip()

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Replace <li> with bullet characters
        for li in soup.find_all("li"):
            li.insert_before("• ")
            li.append("\n")

        # Replace block tags with newlines
        for block in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section"]):
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
        return result or html_content.strip()
    except Exception:
        # Fallback to regex strip if parser fails
        clean = re.sub(r"<[^>]+>", " ", html_content)
        return re.sub(r"\s+", " ", clean).strip()


def generate_fingerprint(normalized_company: str, normalized_title: str, city: Optional[str]) -> str:
    """Generates sha256 fingerprint from norm_company | norm_title | city.lower()."""
    city_str = (city or "unspecified").strip().lower()
    raw = f"{normalized_company}|{normalized_title}|{city_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
