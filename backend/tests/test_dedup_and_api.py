import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Job, JobSource
from app.main import app
from app.pipeline import process_raw_jobs
from app.collectors.base import RawJob

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_multi_source_deduplication_and_merging():
    """
    Verifies that duplicate listings across LinkedIn, Naukri, and Greenhouse
    correctly merge into 1 Job row with 3 JobSource records.
    """
    db = TestingSessionLocal()

    # 1. First listing from Greenhouse
    gh_job = RawJob(
        source_name="greenhouse",
        external_id="gh_101",
        title="Senior Software Engineer",
        company="Razorpay Software Pvt Ltd",
        apply_url="https://boards.greenhouse.io/razorpay/jobs/101?utm_source=gh",
        location="Bangalore, India",
        description="<p>Lead backend payment architecture.</p>",
        salary_min=None,
        salary_max=None,
    )
    process_raw_jobs(db, [gh_job], "ats_direct")

    assert db.query(Job).count() == 1
    assert db.query(JobSource).count() == 1
    job = db.query(Job).first()
    assert job.company == "Razorpay Software Pvt Ltd"
    assert job.city == "Bengaluru"
    assert job.sources[0].source_name == "greenhouse"

    # 2. Second listing from LinkedIn (Exact same canonical fingerprint)
    li_job = RawJob(
        source_name="linkedin",
        external_id="li_555",
        title="Senior Software Engineer",
        company="Razorpay",
        apply_url="https://www.linkedin.com/jobs/view/555/?trk=public_jobs",
        location="Bengaluru, Karnataka",
        description="<p>Lead backend payment architecture with higher salary.</p>",
        salary_min=3000000.0,
        salary_max=4500000.0,
        currency="INR",
    )
    process_raw_jobs(db, [li_job], "jobspy")

    # Should still have 1 Job, but now 2 JobSources!
    assert db.query(Job).count() == 1
    assert db.query(JobSource).count() == 2
    refreshed_job = db.query(Job).first()
    assert refreshed_job.salary_min == 3000000.0
    assert refreshed_job.salary_max == 4500000.0
    assert refreshed_job.currency == "INR"

    # 3. Third listing from Naukri (Fuzzy title variation: "Sr. Software Engineer")
    naukri_job = RawJob(
        source_name="naukri",
        external_id="nk_999",
        title="Sr. Software Engineer",
        company="Razorpay",
        apply_url="https://www.naukri.com/job-listings-999?ref=home",
        location="Bengaluru",
        description="Requirements: 5-8 yrs experience",
        min_exp=5.0,
        max_exp=8.0,
    )
    process_raw_jobs(db, [naukri_job], "jobspy")

    # Tier 3 fuzzy matching should merge this into the existing job!
    assert db.query(Job).count() == 1
    assert db.query(JobSource).count() == 3

    source_names = {s.source_name for s in refreshed_job.sources}
    assert source_names == {"greenhouse", "linkedin", "naukri"}
    assert refreshed_job.min_exp == 5.0
    assert refreshed_job.max_exp == 8.0

    db.close()


def test_api_endpoints_and_tracking(monkeypatch):
    monkeypatch.setattr("app.main.run_ingestion", lambda *args, **kwargs: [])
    client = TestClient(app)

    # 1. Health endpoint
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "ok"
    assert "total_jobs" in health_data

    # 2. Seed a job via database
    db = TestingSessionLocal()
    seed_job = RawJob(
        source_name="ashby",
        external_id="ashby_linear_01",
        title="Full Stack Product Engineer",
        company="Linear",
        apply_url="https://jobs.ashbyhq.com/linear/01",
        location="Remote",
        is_remote=True,
        description="Build magical issue tracking software.",
        salary_min=160000.0,
        salary_max=210000.0,
        currency="USD",
        min_exp=2.0,
        max_exp=5.0,
    )
    process_raw_jobs(db, [seed_job], "ats_direct")
    job_id = db.query(Job).first().id
    db.close()

    # 3. GET /api/jobs
    jobs_resp = client.get("/api/jobs")
    assert jobs_resp.status_code == 200
    jobs_data = jobs_resp.json()
    assert jobs_data["total"] == 1
    assert jobs_data["jobs"][0]["company"] == "Linear"
    assert len(jobs_data["jobs"][0]["sources"]) == 1
    assert jobs_data["jobs"][0]["sources"][0]["source_name"] == "ashby"

    # 3b. Test multi-token search and exp_years filter
    search_resp = client.get("/api/jobs?q=Full+Stack")
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] == 1

    exp_resp = client.get("/api/jobs?exp_years=4")
    assert exp_resp.status_code == 200
    assert exp_resp.json()["total"] == 1

    # 4. GET /api/jobs/{id}
    single_resp = client.get(f"/api/jobs/{job_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["id"] == job_id

    # 5. PATCH /api/jobs/{id}/track
    # Setting status to 'applied' must auto-set is_saved=True
    patch_resp = client.patch(
        f"/api/jobs/{job_id}/track",
        json={"application_status": "applied", "notes": "Applied via referral on Monday"},
    )
    assert patch_resp.status_code == 200
    tracked_data = patch_resp.json()
    assert tracked_data["application_status"] == "applied"
    assert tracked_data["is_saved"] is True
    assert tracked_data["notes"] == "Applied via referral on Monday"

    # 6. GET /api/filters
    filter_resp = client.get("/api/filters")
    assert filter_resp.status_code == 200
    f_data = filter_resp.json()
    assert f_data["kpis"]["total_jobs"] == 1
    assert f_data["kpis"]["saved_jobs"] == 1
    assert f_data["kpis"]["applied_jobs"] == 1
    assert f_data["kpis"]["active_sources"] == 1

    # 6b. GET /api/stats (Dedicated KPI endpoint)
    stats_resp = client.get("/api/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["total_jobs"] == 1
    assert stats_data["applied_jobs"] == 1

    # 6c. Universal Dynamic Cross-Faceting on /api/filters
    # exp_years=4 should find Linear in companies
    f_exp4 = client.get("/api/filters?exp_years=4")
    assert f_exp4.status_code == 200
    companies_exp4 = [c["name"] for c in f_exp4.json()["companies"]]
    assert "Linear" in companies_exp4

    # exp_years=10 should exclude Linear (strict non-zero rule)
    f_exp10 = client.get("/api/filters?exp_years=10")
    assert f_exp10.status_code == 200
    companies_exp10 = [c["name"] for c in f_exp10.json()["companies"]]
    assert "Linear" not in companies_exp10

    # 7. GET /api/sync/status
    sync_status = client.get("/api/sync/status")
    assert sync_status.status_code == 200
    assert "is_running" in sync_status.json()

    # 8. POST /api/sync
    trigger_resp = client.post("/api/sync?mode=fast")
    assert trigger_resp.status_code == 200
    assert trigger_resp.json()["status"] in ["started", "busy"]
