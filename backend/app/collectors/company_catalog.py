"""
Dynamic Company Catalog for Multi-ATS Ingestion.
Catalogs top global tech firms, startups, and Indian MNCs across Greenhouse, Lever, Ashby, and SmartRecruiters.
Covers cities worldwide: Pune, Mumbai, Bengaluru, Hyderabad, Delhi NCR, London, Berlin, Singapore, Tokyo, New York, San Francisco, and Remote.
"""

# ---------------------------------------------------------------------------
# Greenhouse Boards (Public JSON API: boards-api.greenhouse.io/v1/boards/{slug}/jobs)
# ---------------------------------------------------------------------------
GREENHOUSE_GLOBAL_CATALOG = [
    # Pune & Mumbai Tech Hubs
    "pubmatic",
    "ensono",
    "rubrik",
    "zocdoc",
    "druva",
    "ivalua",
    "inmobi",
    "groww",
    # Global Tech Giants & Innovators
    "stripe",
    "gitlab",
    "figma",
    "cloudflare",
    "airbnb",
    "databricks",
    "coinbase",
    "reddit",
    "discord",
    "canva",
    "pinterest",
    "twitch",
    "doordash",
    "instacart",
    "chime",
    "robinhood",
    "gusto",
    "affirm",
    "brex",
    "carta",
    "flexport",
    "benchling",
    "scale",
    "samsara",
    "mongodb",
    "elastic",
    "hashicorp",
    "pagerduty",
    "datadog",
    "okta",
    "crowdstrike",
]

# ---------------------------------------------------------------------------
# Lever Boards (Public JSON API: api.lever.co/v0/postings/{slug}?mode=json)
# ---------------------------------------------------------------------------
LEVER_GLOBAL_CATALOG = [
    # India & Global Hubs
    "mindtickle",
    "atlassian",
    "spotify",
    "netflix",
    "plaid",
    "revolut",
    "monzo",
    "klarna",
    "n26",
    "clevertap",
    "upstox",
    "auth0",
    "deliveroo",
    "transferwise",
    "eventbrite",
    "lyft",
    "box",
    "automattic",
    "coursera",
    "udemy",
]

# ---------------------------------------------------------------------------
# Ashby Boards (Public JSON API: api.ashbyhq.com/posting-api/job-board/{slug})
# ---------------------------------------------------------------------------
ASHBY_GLOBAL_CATALOG = [
    "linear",
    "ramp",
    "notion",
    "vercel",
    "openai",
    "elevenlabs",
    "perplexity",
    "retool",
    "supabase",
    "neon",
    "resend",
    "cursor",
    "anthropic",
]

# ---------------------------------------------------------------------------
# SmartRecruiters Boards (Public JSON API: api.smartrecruiters.com/v1/companies/{slug}/postings)
# ---------------------------------------------------------------------------
SMARTRECRUITERS_GLOBAL_CATALOG = [
    "visa",
    "bosch",
    "wipro",
    "publicissapient",
    "ikea",
    "square",
]
