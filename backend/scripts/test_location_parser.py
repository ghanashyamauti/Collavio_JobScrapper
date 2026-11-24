import re
import pycountry
from typing import Optional, Tuple, Dict, Set

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
    "mh": "India", "ka": "India", "ts": "India", "tn": "India", "hr": "India", "up": "India",
    "gj": "India", "wb": "India", "kl": "India", "dl": "India"
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
    "belfast": ("Belfast", "United Kingdom"), "cambridge uk": ("Cambridge", "United Kingdom"),

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

print("Total countries/aliases loaded:", len(COUNTRY_ALIASES))

# Test parsing function
def parse_location(loc_raw: str, title: str = ""):
    loc_str = (loc_raw or "").strip()
    combined = f"{loc_str} {title}".lower()
    is_remote = any(re.search(rf"\b{kw}\b", combined, re.IGNORECASE) for kw in ["remote", "work from home", "wfh", "anywhere", "worldwide"])

    detected_country = None
    detected_city = None

    # Step A: Clean tokens by splitting on delimiters
    tokens = [t.strip() for t in re.split(r"[,/|;>•\-]", loc_str) if t.strip()]

    # Check tokens right-to-left for Country
    for t in reversed(tokens):
        t_clean = re.sub(r"[^\w\s]", "", t).strip().lower()
        if t_clean in COUNTRY_ALIASES:
            detected_country = COUNTRY_ALIASES[t_clean]
            break
        # Check pycountry alpha_2/alpha_3 exact token match
        if len(t) in (2, 3) and t.isupper():
            try:
                c_obj = pycountry.countries.get(alpha_2=t) or pycountry.countries.get(alpha_3=t)
                if c_obj:
                    detected_country = c_obj.name
                    break
            except Exception:
                pass

    # Check tokens for State / Province
    for t in tokens:
        t_lower = t.lower()
        if t_lower in US_STATE_CODES or t_lower in US_STATE_NAMES:
            detected_country = detected_country or "United States"
        elif t_lower in CA_PROV_CODES or t_lower in CA_PROV_NAMES:
            detected_country = detected_country or "Canada"
        elif t_lower in AU_STATE_CODES or t_lower in AU_STATE_NAMES:
            detected_country = detected_country or "Australia"
        elif t_lower in IN_STATES:
            detected_country = detected_country or "India"

    # Check for US state abbreviation patterns e.g. "Austin, TX"
    m_us_state = re.search(r",\s*([A-Z]{2})\b", loc_str)
    if m_us_state:
        st = m_us_state.group(1).lower()
        if st in US_STATE_CODES and not detected_country:
            detected_country = "United States"
        elif st in CA_PROV_CODES and not detected_country:
            detected_country = "Canada"

    # Step B: Check for City
    # 1. Exact token match against GLOBAL_CITIES
    for t in tokens:
        t_clean = re.sub(r"[^\w\s]", "", t).strip().lower()
        if t_clean in GLOBAL_CITIES:
            std_city, std_country = GLOBAL_CITIES[t_clean]
            detected_city = std_city
            detected_country = detected_country or std_country
            break

    # 2. Substring match across full string if not found
    if not detected_city:
        loc_lower = loc_str.lower()
        for alias, (std_city, std_country) in GLOBAL_CITIES.items():
            if re.search(rf"\b{re.escape(alias)}\b", loc_lower):
                detected_city = std_city
                detected_country = detected_country or std_country
                break

    # Step C: Fallbacks
    if not detected_country:
        if is_remote or loc_str.lower() in ("remote", "anywhere", "worldwide", "home based", "wfh"):
            detected_country = "Remote / Worldwide"
        else:
            detected_country = "Global"

    if not detected_city:
        if is_remote:
            detected_city = "Remote"
        elif tokens:
            # First meaningful word if plausible
            detected_city = tokens[0][:30]

    return loc_str or "Remote", detected_city, is_remote, detected_country

# Test cases
test_cases = [
    ("Toronto, ON, Canada", "Software Engineer"),
    ("Vancouver, BC", "Full Stack"),
    ("Amsterdam, Netherlands", "Backend Developer"),
    ("Paris, France", "Product Designer"),
    ("9th arrondissement of Paris, 75009, Paris, France", "Lead"),
    ("Dublin, Ireland", "Data Engineer"),
    ("Sydney, NSW, Australia", "DevOps"),
    ("Singapore", "Engineering Manager"),
    ("Tokyo, Japan", "Frontend"),
    ("Dubai, United Arab Emirates", "Sales Lead"),
    ("Madrid, Spain", "Architect"),
    ("São Paulo, Brazil", "Mobile Dev"),
    ("Bengaluru, Karnataka, India", "Backend Engineer"),
    ("Pune, Maharashtra", "React Dev"),
    ("Austin, TX", "Go Engineer"),
    ("US > Arizona > Phoenix", "Platform Eng"),
    ("Remote - US", "Staff Engineer"),
    ("Remote, Worldwide", "Principal"),
    ("Home based - EMEA", "Account Exec"),
    ("London, UK", "Quant"),
    ("Berlin, Germany", "Rust Dev"),
]

print("\n--- TEST PARSER RESULTS ---")
for loc, title in test_cases:
    clean_loc, city, is_rem, country = parse_location(loc, title)
    print(f"'{loc}' -> City: '{city}' | Country: '{country}' | Remote: {is_rem}")
