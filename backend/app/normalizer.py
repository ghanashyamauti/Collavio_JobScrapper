import re
import html
import hashlib
from typing import Optional, Tuple, Dict, Set
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from bs4 import BeautifulSoup
import pycountry


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

# 1. US State 2-letter codes and names
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia"
}
US_STATE_NAMES = {v.lower(): "United States" for v in US_STATES.values()}
US_STATE_CODES = {k.lower(): "United States" for k in US_STATES.keys()}

# 2. Canada Province codes and names
CA_PROVINCES = {
    "ON": "Ontario", "BC": "British Columbia", "QC": "Quebec", "AB": "Alberta",
    "MB": "Manitoba", "SK": "Saskatchewan", "NS": "Nova Scotia", "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador", "PE": "Prince Edward Island", "NT": "Northwest Territories",
    "YT": "Yukon", "NU": "Nunavut"
}
CA_PROV_NAMES = {v.lower(): "Canada" for v in CA_PROVINCES.values()}
CA_PROV_CODES = {k.lower(): "Canada" for k in CA_PROVINCES.keys()}

# 3. Australia State codes and names
AU_STATES = {
    "NSW": "New South Wales", "VIC": "Victoria", "QLD": "Queensland", "WA": "Western Australia",
    "SA": "South Australia", "TAS": "Tasmania", "ACT": "Australian Capital Territory", "NT": "Northern Territory"
}
AU_STATE_NAMES = {v.lower(): "Australia" for v in AU_STATES.values()}
AU_STATE_CODES = {k.lower(): "Australia" for k in AU_STATES.keys()}

# 4. India State names and codes
IN_STATES = {
    "karnataka": "India", "maharashtra": "India", "telangana": "India", "tamil nadu": "India",
    "delhi": "India", "haryana": "India", "uttar pradesh": "India", "gujarat": "India",
    "west bengal": "India", "kerala": "India", "rajasthan": "India", "madhya pradesh": "India",
    "punjab": "India", "andhra pradesh": "India", "bihar": "India", "odisha": "India",
    "assam": "India", "goa": "India", "jharkhand": "India", "uttarakhand": "India",
}

# 5. Global Cities -> (Standard City Name, Standard Country Name)
GLOBAL_CITIES = {
    # India
    "bengaluru": ("Bengaluru", "India"), "bangalore": ("Bengaluru", "India"),
    "mumbai": ("Mumbai", "India"), "bombay": ("Mumbai", "India"),
    "pune": ("Pune", "India"), "hyderabad": ("Hyderabad", "India"),
    "gurgaon": ("Gurugram", "India"), "gurugram": ("Gurugram", "India"),
    "delhi": ("Delhi", "India"), "new delhi": ("Delhi", "India"),
    "delhi ncr": ("Delhi NCR", "India"), "noida": ("Noida", "India"),
    "greater noida": ("Noida", "India"), "chennai": ("Chennai", "India"),
    "madras": ("Chennai", "India"), "kolkata": ("Kolkata", "India"),
    "calcutta": ("Kolkata", "India"), "ahmedabad": ("Ahmedabad", "India"),
    "jaipur": ("Jaipur", "India"), "surat": ("Surat", "India"),
    "indore": ("Indore", "India"), "nagpur": ("Nagpur", "India"),
    "chandigarh": ("Chandigarh", "India"), "kochi": ("Kochi", "India"),
    "cochin": ("Kochi", "India"), "coimbatore": ("Coimbatore", "India"),
    "bhubaneswar": ("Bhubaneswar", "India"), "thiruvananthapuram": ("Thiruvananthapuram", "India"),
    "trivandrum": ("Thiruvananthapuram", "India"), "lucknow": ("Lucknow", "India"),
    "vadodara": ("Vadodara", "India"), "visakhapatnam": ("Visakhapatnam", "India"),
    "patna": ("Patna", "India"), "bhopal": ("Bhopal", "India"),
    "mysuru": ("Mysuru", "India"), "mysore": ("Mysuru", "India"),
    "kanpur": ("Kanpur", "India"), "ludhiana": ("Ludhiana", "India"),
    "nashik": ("Nashik", "India"), "dehradun": ("Dehradun", "India"),
    "ranchi": ("Ranchi", "India"), "guwahati": ("Guwahati", "India"),

    # United States
    "new york": ("New York", "United States"), "nyc": ("New York", "United States"),
    "new york city": ("New York", "United States"), "san francisco": ("San Francisco", "United States"),
    "sf": ("San Francisco", "United States"), "seattle": ("Seattle", "United States"),
    "austin": ("Austin", "United States"), "boston": ("Boston", "United States"),
    "chicago": ("Chicago", "United States"), "los angeles": ("Los Angeles", "United States"),
    "la": ("Los Angeles", "United States"), "denver": ("Denver", "United States"),
    "atlanta": ("Atlanta", "United States"), "san jose": ("San Jose", "United States"),
    "dallas": ("Dallas", "United States"), "houston": ("Houston", "United States"),
    "san diego": ("San Diego", "United States"), "miami": ("Miami", "United States"),
    "portland": ("Portland", "United States"), "phoenix": ("Phoenix", "United States"),
    "philadelphia": ("Philadelphia", "United States"), "washington": ("Washington", "United States"),
    "washington dc": ("Washington", "United States"), "pittsburgh": ("Pittsburgh", "United States"),
    "raleigh": ("Raleigh", "United States"), "salt lake city": ("Salt Lake City", "United States"),
    "minneapolis": ("Minneapolis", "United States"), "detroit": ("Detroit", "United States"),
    "charlotte": ("Charlotte", "United States"), "tampa": ("Tampa", "United States"),
    "nashville": ("Nashville", "United States"), "palo alto": ("Palo Alto", "United States"),
    "mountain view": ("Mountain View", "United States"), "sunnyvale": ("Sunnyvale", "United States"),
    "redwood city": ("Redwood City", "United States"), "santa clara": ("Santa Clara", "United States"),
    "menlo park": ("Menlo Park", "United States"), "cupertino": ("Cupertino", "United States"),
    "berkeley": ("Berkeley", "United States"), "oakland": ("Oakland", "United States"),
    "irvine": ("Irvine", "United States"), "bellevue": ("Bellevue", "United States"),
    "redmond": ("Redmond", "United States"), "arlington": ("Arlington", "United States"),
    "mclean": ("McLean", "United States"), "cambridge": ("Cambridge", "United States"),
    "indianapolis": ("Indianapolis", "United States"), "memphis": ("Memphis", "United States"),
    "plainfield": ("Plainfield", "United States"), "greenfield": ("Greenfield", "United States"),

    # Canada
    "toronto": ("Toronto", "Canada"), "vancouver": ("Vancouver", "Canada"),
    "montreal": ("Montreal", "Canada"), "montréal": ("Montreal", "Canada"),
    "calgary": ("Calgary", "Canada"), "ottawa": ("Ottawa", "Canada"),
    "edmonton": ("Edmonton", "Canada"), "waterloo": ("Waterloo", "Canada"),
    "mississauga": ("Mississauga", "Canada"), "quebec": ("Quebec City", "Canada"),
    "quebec city": ("Quebec City", "Canada"), "victoria": ("Victoria", "Canada"),
    "halifax": ("Halifax", "Canada"), "winnipeg": ("Winnipeg", "Canada"),

    # United Kingdom
    "london": ("London", "United Kingdom"), "manchester": ("Manchester", "United Kingdom"),
    "edinburgh": ("Edinburgh", "United Kingdom"), "birmingham": ("Birmingham", "United Kingdom"),
    "bristol": ("Bristol", "United Kingdom"), "glasgow": ("Glasgow", "United Kingdom"),
    "leeds": ("Leeds", "United Kingdom"), "oxford": ("Oxford", "United Kingdom"),
    "belfast": ("Belfast", "United Kingdom"),

    # Germany
    "berlin": ("Berlin", "Germany"), "munich": ("Munich", "Germany"), "münchen": ("Munich", "Germany"),
    "frankfurt": ("Frankfurt", "Germany"), "hamburg": ("Hamburg", "Germany"),
    "cologne": ("Cologne", "Germany"), "köln": ("Cologne", "Germany"),
    "stuttgart": ("Stuttgart", "Germany"), "dusseldorf": ("Dusseldorf", "Germany"),
    "düsseldorf": ("Dusseldorf", "Germany"),

    # France
    "paris": ("Paris", "France"), "lyon": ("Lyon", "France"),
    "marseille": ("Marseille", "France"), "toulouse": ("Toulouse", "France"),
    "nice": ("Nice", "France"), "bordeaux": ("Bordeaux", "France"),
    "nantes": ("Nantes", "France"),

    # Netherlands
    "amsterdam": ("Amsterdam", "Netherlands"), "rotterdam": ("Rotterdam", "Netherlands"),
    "the hague": ("The Hague", "Netherlands"), "den haag": ("The Hague", "Netherlands"),
    "utrecht": ("Utrecht", "Netherlands"), "eindhoven": ("Eindhoven", "Netherlands"),

    # Ireland
    "dublin": ("Dublin", "Ireland"), "cork": ("Cork", "Ireland"),
    "galway": ("Galway", "Ireland"), "limerick": ("Limerick", "Ireland"),

    # Australia
    "sydney": ("Sydney", "Australia"), "melbourne": ("Melbourne", "Australia"),
    "brisbane": ("Brisbane", "Australia"), "perth": ("Perth", "Australia"),
    "adelaide": ("Adelaide", "Australia"), "canberra": ("Canberra", "Australia"),

    # Singapore
    "singapore": ("Singapore", "Singapore"),

    # UAE
    "dubai": ("Dubai", "United Arab Emirates"), "abu dhabi": ("Abu Dhabi", "United Arab Emirates"),
    "sharjah": ("Sharjah", "United Arab Emirates"),

    # Spain
    "madrid": ("Madrid", "Spain"), "barcelona": ("Barcelona", "Spain"),
    "valencia": ("Valencia", "Spain"), "seville": ("Seville", "Spain"),

    # Italy
    "rome": ("Rome", "Italy"), "milan": ("Milan", "Italy"), "milano": ("Milan", "Italy"),
    "turin": ("Turin", "Italy"), "florence": ("Florence", "Italy"),

    # Japan
    "tokyo": ("Tokyo", "Japan"), "osaka": ("Osaka", "Japan"), "kyoto": ("Kyoto", "Japan"),

    # Poland
    "warsaw": ("Warsaw", "Poland"), "krakow": ("Krakow", "Poland"), "kraków": ("Krakow", "Poland"),
    "wroclaw": ("Wroclaw", "Poland"), "wrocław": ("Wroclaw", "Poland"),

    # Sweden
    "stockholm": ("Stockholm", "Sweden"), "gothenburg": ("Gothenburg", "Sweden"),
    "malmo": ("Malmo", "Sweden"), "malmö": ("Malmo", "Sweden"),

    # Switzerland
    "zurich": ("Zurich", "Switzerland"), "zürich": ("Zurich", "Switzerland"),
    "geneva": ("Geneva", "Switzerland"), "genève": ("Geneva", "Switzerland"),
    "basel": ("Basel", "Switzerland"), "bern": ("Bern", "Switzerland"),

    # Brazil
    "sao paulo": ("Sao Paulo", "Brazil"), "são paulo": ("Sao Paulo", "Brazil"),
    "rio de janeiro": ("Rio de Janeiro", "Brazil"), "curitiba": ("Curitiba", "Brazil"),

    # Mexico
    "mexico city": ("Mexico City", "Mexico"), "guadalajara": ("Guadalajara", "Mexico"),
    "monterrey": ("Monterrey", "Mexico"),

    # Philippines
    "manila": ("Manila", "Philippines"), "taguig": ("Taguig", "Philippines"),
    "makati": ("Makati", "Philippines"), "cebu": ("Cebu", "Philippines"),

    # Israel
    "tel aviv": ("Tel Aviv", "Israel"), "jerusalem": ("Jerusalem", "Israel"),
    "herzliya": ("Herzliya", "Israel"),

    # New Zealand
    "auckland": ("Auckland", "New Zealand"), "wellington": ("Wellington", "New Zealand"),

    # Thailand
    "bangkok": ("Bangkok", "Thailand"),

    # Hong Kong & Taiwan
    "hong kong": ("Hong Kong", "Hong Kong"), "taipei": ("Taipei", "Taiwan"),

    # South Korea
    "seoul": ("Seoul", "South Korea"),
}

CITY_ALIASES = {k: v[0] for k, v in GLOBAL_CITIES.items()}
CITY_ALIASES["remote"] = "Remote"

# 6. Standard Country Aliases Map
COUNTRY_ALIASES = {
    "united states": "United States", "usa": "United States", "u.s.": "United States", "u.s.a.": "United States", "us": "United States",
    "united kingdom": "United Kingdom", "uk": "United Kingdom", "great britain": "United Kingdom", "england": "United Kingdom", "scotland": "United Kingdom", "wales": "United Kingdom",
    "india": "India", "in": "India",
    "canada": "Canada", "ca": "Canada",
    "germany": "Germany", "deutschland": "Germany", "de": "Germany",
    "france": "France", "fr": "France",
    "netherlands": "Netherlands", "holland": "Netherlands", "nl": "Netherlands",
    "ireland": "Ireland", "ie": "Ireland",
    "australia": "Australia", "au": "Australia",
    "singapore": "Singapore", "sg": "Singapore",
    "united arab emirates": "United Arab Emirates", "uae": "United Arab Emirates", "ae": "United Arab Emirates",
    "spain": "Spain", "españa": "Spain", "es": "Spain",
    "italy": "Italy", "italia": "Italy", "it": "Italy",
    "japan": "Japan", "jp": "Japan",
    "brazil": "Brazil", "brasil": "Brazil", "br": "Brazil",
    "poland": "Poland", "polska": "Poland", "pl": "Poland",
    "sweden": "Sweden", "sverige": "Sweden", "se": "Sweden",
    "switzerland": "Switzerland", "schweiz": "Switzerland", "suisse": "Switzerland", "ch": "Switzerland",
    "mexico": "Mexico", "méxico": "Mexico", "mx": "Mexico",
    "philippines": "Philippines", "ph": "Philippines",
    "israel": "Israel", "il": "Israel",
    "new zealand": "New Zealand", "nz": "New Zealand",
    "thailand": "Thailand", "th": "Thailand",
    "hong kong": "Hong Kong", "hk": "Hong Kong",
    "taiwan": "Taiwan", "tw": "Taiwan",
    "south korea": "South Korea", "korea": "South Korea", "kr": "South Korea",
    "china": "China", "cn": "China",
    "portugal": "Portugal", "pt": "Portugal",
    "austria": "Austria", "österreich": "Austria", "at": "Austria",
    "belgium": "Belgium", "be": "Belgium",
    "denmark": "Denmark", "danmark": "Denmark", "dk": "Denmark",
    "norway": "Norway", "norge": "Norway", "no": "Norway",
    "finland": "Finland", "suomi": "Finland", "fi": "Finland",
    "czech republic": "Czech Republic", "czechia": "Czech Republic", "cz": "Czech Republic",
    "romania": "Romania", "ro": "Romania",
    "greece": "Greece", "gr": "Greece",
    "turkey": "Turkey", "türkiye": "Turkey", "tr": "Turkey",
    "south africa": "South Africa", "za": "South Africa",
    "argentina": "Argentina", "ar": "Argentina",
    "colombia": "Colombia", "co": "Colombia",
    "chile": "Chile", "cl": "Chile",
    "egypt": "Egypt", "eg": "Egypt",
    "nigeria": "Nigeria", "ng": "Nigeria",
    "kenya": "Kenya", "ke": "Kenya",
    "vietnam": "Vietnam", "vn": "Vietnam",
    "indonesia": "Indonesia", "id": "Indonesia",
    "malaysia": "Malaysia", "my": "Malaysia",
}

# Fill additional countries from pycountry
for country in pycountry.countries:
    cname = country.name
    cname_lower = cname.lower()
    if cname_lower not in COUNTRY_ALIASES:
        COUNTRY_ALIASES[cname_lower] = cname
    if hasattr(country, "common_name") and country.common_name.lower() not in COUNTRY_ALIASES:
        COUNTRY_ALIASES[country.common_name.lower()] = country.common_name

REMOTE_KEYWORDS = [
    "remote", "work from home", "wfh", "worldwide", "anywhere",
    "telecommute", "home based", "home-based"
]

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
    is_remote = any(re.search(rf"\b{re.escape(kw)}\b", combined, re.IGNORECASE) for kw in REMOTE_KEYWORDS)

    matched_city = None
    loc_lower = loc_str.lower()

    # 1. Clean tokens by splitting on delimiters
    tokens = [t.strip() for t in re.split(r"[,/|;>•\-]", loc_str) if t.strip()]

    # 2. Check tokens against GLOBAL_CITIES
    for t in tokens:
        t_clean = re.sub(r"[^\w\s]", "", t).strip().lower()
        if t_clean in GLOBAL_CITIES:
            matched_city = GLOBAL_CITIES[t_clean][0]
            break

    # 3. Fast n-gram check in CITY_ALIASES if still not matched
    if not matched_city:
        words = re.findall(r"\b[a-z]{2,}\b", loc_lower)
        for w in words:
            if w in CITY_ALIASES:
                matched_city = CITY_ALIASES[w]
                break
        if not matched_city:
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if phrase in CITY_ALIASES:
                    matched_city = CITY_ALIASES[phrase]
                    break
        if not matched_city:
            for i in range(len(words) - 2):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                if phrase in CITY_ALIASES:
                    matched_city = CITY_ALIASES[phrase]
                    break

    if not matched_city and is_remote:
        matched_city = "Remote"
    elif not matched_city and tokens and len(tokens[0]) <= 30 and not re.search(r"\d", tokens[0]):
        first_token = tokens[0].strip()
        f_lower = first_token.lower()
        non_cities = {
            "hybrid", "unspecified", "multiple", "various", "onsite", "on-site", "flexible",
            "remote", "worldwide", "global", "india", "in", "us", "usa", "uk", "united states",
            "united kingdom", "germany", "canada", "australia", "france"
        }
        if f_lower not in non_cities and f_lower not in COUNTRY_ALIASES:
            matched_city = first_token.title()

    if not loc_str and is_remote:
        loc_str = "Remote"

    return loc_str or ("Remote" if is_remote else "Unspecified"), matched_city, is_remote


def detect_country(location: Optional[str], city: Optional[str] = None, is_remote: bool = False) -> str:
    """
    Classifies job location into a standardized worldwide country name.
    Utilizes pycountry, state/province mappings, global city mappings, and hierarchical token matching.
    Reserves 'Remote / Worldwide' only for location-agnostic remote roles.
    """
    loc_str = (location or "").strip()
    c_str = (city or "").strip().lower()
    combined = f"{loc_str} {c_str}".lower()

    # 1. Explicit check for India: mentions 'india' as a whole word, or Indian city/state
    if (
        bool(re.search(r"\bindia\b", combined))
        or (c_str in GLOBAL_CITIES and GLOBAL_CITIES[c_str][1] == "India")
        or any(re.search(rf"\b{re.escape(k)}\b", combined) for k in IN_STATES)
    ):
        return "India"

    # 2. Check City if provided and in GLOBAL_CITIES
    if c_str and c_str in GLOBAL_CITIES:
        return GLOBAL_CITIES[c_str][1]

    # 3. Check for US/Canada/Australia State abbreviation e.g. ", CA", ", IN", ", TX", or State Name
    m_us_state = re.search(r",\s*([A-Z]{2})\b", loc_str)
    if m_us_state:
        st = m_us_state.group(1).lower()
        if st in US_STATE_CODES:
            return "United States"
        if st in CA_PROV_CODES:
            return "Canada"
        if st in AU_STATE_CODES:
            return "Australia"

    tokens = [t.strip() for t in re.split(r"[,/|;>•\-]", loc_str) if t.strip()]
    for t in tokens:
        t_lower = t.lower()
        if t_lower in US_STATE_CODES or t_lower in US_STATE_NAMES:
            return "United States"
        if t_lower in CA_PROV_CODES or t_lower in CA_PROV_NAMES:
            return "Canada"
        if t_lower in AU_STATE_CODES or t_lower in AU_STATE_NAMES:
            return "Australia"
        if t_lower in IN_STATES:
            return "India"

    # 4. Clean tokens right-to-left for Country Name / Alias
    for t in reversed(tokens):
        t_clean = re.sub(r"[^\w\s]", "", t).strip().lower()
        if t_clean in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[t_clean]
        # Check pycountry alpha_2/alpha_3 exact token match
        if len(t) in (2, 3) and t.isupper():
            try:
                c_obj = pycountry.countries.get(alpha_2=t) or pycountry.countries.get(alpha_3=t)
                if c_obj:
                    return c_obj.name
            except Exception:
                pass

    # 5. Fast word & phrase lookup in GLOBAL_CITIES and COUNTRY_ALIASES
    loc_lower = loc_str.lower()
    words = re.findall(r"\b[a-z]{2,}\b", loc_lower)
    for w in words:
        if w in GLOBAL_CITIES:
            return GLOBAL_CITIES[w][1]
        if w in COUNTRY_ALIASES and len(w) >= 3:
            return COUNTRY_ALIASES[w]

    for i in range(len(words) - 1):
        phrase = f"{words[i]} {words[i+1]}"
        if phrase in GLOBAL_CITIES:
            return GLOBAL_CITIES[phrase][1]
        if phrase in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[phrase]

    for i in range(len(words) - 2):
        phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
        if phrase in GLOBAL_CITIES:
            return GLOBAL_CITIES[phrase][1]
        if phrase in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[phrase]

    # 7. Check Remote status
    if is_remote or any(re.search(rf"\b{re.escape(kw)}\b", loc_lower) for kw in REMOTE_KEYWORDS):
        return "Remote / Worldwide"

    return "Global"


def detect_platform_source(source_name: Optional[str], apply_url: Optional[str] = None) -> str:
    """Resolves true platform source name from raw source or apply URL domain."""
    url = (apply_url or "").lower()
    src = (source_name or "").lower().strip()

    valid_platforms = {
        "greenhouse", "lever", "ashby", "smartrecruiters", "workable", "workday",
        "arbeitnow", "himalayas", "jobicy", "remotive", "remoteok", "weworkremotely",
        "themuse", "linkedin", "naukri", "indeed", "glassdoor"
    }
    if src in valid_platforms:
        return src

    if "greenhouse.io" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "ashbyhq.com" in url:
        return "ashby"
    if "smartrecruiters.com" in url:
        return "smartrecruiters"
    if "workable.com" in url:
        return "workable"
    if "myworkdayjobs.com" in url:
        return "workday"
    if "arbeitnow.com" in url:
        return "arbeitnow"
    if "himalayas.app" in url:
        return "himalayas"
    if "jobicy.com" in url:
        return "jobicy"
    if "remotive.com" in url:
        return "remotive"
    if "remoteok.com" in url:
        return "remoteok"
    if "weworkremotely.com" in url:
        return "weworkremotely"
    if "themuse.com" in url:
        return "themuse"
    if "linkedin.com" in url:
        return "linkedin"
    if "naukri.com" in url:
        return "naukri"
    if "indeed.com" in url:
        return "indeed"
    if "glassdoor.com" in url:
        return "glassdoor"

    return src if src and src not in ("ats_direct", "public_feeds") else "other"


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
        # Cap description at 5,000 characters to prevent TOAST table bloat
        # and allow 100,000+ jobs to fit efficiently in database storage
        if len(result) > 5000:
            result = result[:5000].rsplit(" ", 1)[0] + "..."
        return result or content.strip()[:5000]
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
