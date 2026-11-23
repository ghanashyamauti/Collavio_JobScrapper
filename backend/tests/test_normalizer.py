import pytest
from app.normalizer import (
    canonicalize_url,
    normalize_company,
    normalize_title,
    normalize_location_and_remote,
    classify_category,
    parse_experience,
    clean_html_description,
    generate_fingerprint,
)


def test_url_canonicalization():
    raw_url = "https://jobs.example.com/posting/123/?utm_source=linkedin&utm_medium=feed&ref=jobboard&trk=public_jobs#section-apply"
    clean = canonicalize_url(raw_url)
    assert "utm_source" not in clean
    assert "utm_medium" not in clean
    assert "ref" not in clean
    assert "trk" not in clean
    assert "#section-apply" not in clean
    assert clean == "https://jobs.example.com/posting/123"

    # Preserves legitimate query parameters
    url_with_page = "https://jobs.example.com/search?q=developer&utm_campaign=winter"
    clean_search = canonicalize_url(url_with_page)
    assert "q=developer" in clean_search
    assert "utm_campaign" not in clean_search


def test_company_normalization():
    assert normalize_company("Stripe Inc.") == "stripe"
    assert normalize_company("Razorpay Software Pvt. Ltd.") == "razorpay"
    assert normalize_company("PhonePe Private Limited") == "phonepe"
    assert normalize_company("Wipro Technologies Solutions Ltd") == "wipro"
    assert normalize_company("Postman Labs Inc") == "postman"


def test_location_and_remote_normalization():
    # Indian city aliasing
    loc, city, is_remote = normalize_location_and_remote("Bangalore, Karnataka", "Software Engineer")
    assert city == "Bengaluru"
    assert not is_remote

    loc, city, is_remote = normalize_location_and_remote("Bombay", "Frontend Dev")
    assert city == "Mumbai"

    loc, city, is_remote = normalize_location_and_remote("Gurgaon", "Backend Dev")
    assert city == "Gurugram"

    loc, city, is_remote = normalize_location_and_remote("New Delhi", "Data Scientist")
    assert city == "Delhi"

    # Global city aliasing
    loc, city, is_remote = normalize_location_and_remote("NYC, NY", "Product Designer")
    assert city == "New York"

    loc, city, is_remote = normalize_location_and_remote("San Francisco, CA", "Full Stack")
    assert city == "San Francisco"

    # Remote detection
    loc, city, is_remote = normalize_location_and_remote("Remote - US", "Staff Engineer (WFH)")
    assert is_remote is True
    assert city == "Remote"

    loc, city, is_remote = normalize_location_and_remote("Bengaluru", "DevOps Engineer (Work from home)")
    assert is_remote is True
    assert city == "Bengaluru"


def test_category_classification():
    # Tech categories
    assert classify_category("Senior Python Backend Engineer") == "Engineering"
    assert classify_category("Full Stack Developer") == "Engineering"
    assert classify_category("Senior Data Scientist - NLP") == "Data & AI"
    assert classify_category("Lead Machine Learning Engineer") == "Data & AI"
    assert classify_category("Technical Product Manager") == "Product"
    assert classify_category("Principal UI/UX Designer") == "Design"

    # Non-Tech corporate categories
    assert classify_category("Growth Marketing Specialist") == "Marketing"
    assert classify_category("Enterprise Account Executive (SDR)") == "Sales & Growth"
    assert classify_category("Senior Financial Analyst & Controller") == "Finance & Legal"
    assert classify_category("Technical Talent Acquisition Partner (HR)") == "HR & Recruiting"
    assert classify_category("Customer Support Operations Lead") == "Operations & Support"

    # Fallback
    assert classify_category("Executive Driver") == "Other"


def test_experience_parsing():
    # Range regex
    min_e, max_e = parse_experience("Software Engineer", "Looking for 2-4 yrs experience in Python")
    assert min_e == 2.0
    assert max_e == 4.0

    min_e, max_e = parse_experience("Full Stack Developer", "Requires 3 to 5 years of hands-on React")
    assert min_e == 3.0
    assert max_e == 5.0

    # Single bound regex
    min_e, max_e = parse_experience("DevOps Lead", "Minimum 5+ years building AWS infrastructure")
    assert min_e == 5.0
    assert max_e is None

    # Title seniority fallbacks
    min_e, max_e = parse_experience("Software Engineering Intern", "Excited to learn fast")
    assert min_e == 0.0
    assert max_e == 1.0

    min_e, max_e = parse_experience("Junior Associate Developer", "Fresh projects")
    assert min_e == 0.0
    assert max_e == 2.0

    min_e, max_e = parse_experience("Senior Backend Engineer", "Scale our distributed systems")
    assert min_e == 5.0
    assert max_e == 9.0

    min_e, max_e = parse_experience("Staff Software Architect", "Architect platforms")
    assert min_e == 8.0
    assert max_e == 15.0


def test_html_description_cleaner():
    raw_html = """
    <div>
        <h3>About the Role</h3>
        <p>We are seeking a talented engineer.</p>
        <ul>
            <li>Build scalable APIs with FastAPI</li>
            <li>Maintain PostgreSQL pipelines</li>
        </ul>
        <br/>
        <p>Apply today!</p>
    </div>
    """
    clean = clean_html_description(raw_html)
    assert "<h3>" not in clean
    assert "<ul>" not in clean
    assert "• Build scalable APIs with FastAPI" in clean
    assert "• Maintain PostgreSQL pipelines" in clean
    assert "About the Role" in clean
    assert "Apply today!" in clean


def test_fingerprint_generation():
    fp1 = generate_fingerprint("stripe", "software engineer", "Bengaluru")
    fp2 = generate_fingerprint("stripe", "software engineer", "bengaluru")
    fp3 = generate_fingerprint("razorpay", "software engineer", "Bengaluru")

    assert fp1 == fp2  # Case insensitive city
    assert fp1 != fp3
