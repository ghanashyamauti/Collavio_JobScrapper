# Collavio Jobs 🚀

> High-performance, real-time live job scraping, deduplication, and exploration engine indexing 50,000+ active roles directly in Neon Cloud PostgreSQL.

---

## ⚡ Highlights

- **50,000+ Live Verified Roles:** Direct ATS harvesters (Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Workday) + JobSpy (LinkedIn, Naukri, Indeed, Glassdoor) + Public Feeds (Arbeitnow, Himalayas, Remotive, RemoteOK, Jobicy, WeWorkRemotely, The Muse).
- **Sub-Second Search & Cross-Faceting:** Single-round-trip PostgreSQL CTEs, GIN `tsvector` full-text search, trigram indexing, and server-side cached KPI stats.
- **Sleek Single-Thumb Experience Slider:** Range from `Any` to `15+ yrs` with real-time dynamic facet recalculation (0-count items strictly filtered).
- **Non-Blocking Background Live Search:** Seamless fallback to real-time employer searches across LinkedIn, Naukri, and Indeed when database matches are low.
- **On-Demand Live Description Caching:** Lightweight initial ingestion with live description extraction and 404/410 auto-expiration checks.
- **Containerized Deployment:** Dockerfiles for both frontend and backend with multi-stage builds and Docker Compose support.

---

## 🏗️ Architecture

```
Collavio_Job_Scrapper/
├── backend/
│   ├── app/
│   │   ├── collectors/       # ATS (Greenhouse, Lever, Ashby, Workday), JobSpy, Public Feeds
│   │   ├── pipeline.py       # High-speed bulk upsert, deduplication & reconciliation
│   │   ├── normalizer.py     # Location, country, seniority & experience parsing
│   │   ├── database.py       # SQLAlchemy + psycopg connection pooler
│   │   └── main.py           # FastAPI REST endpoints & cached stats
│   ├── data/                 # Curated company ATS catalogs (2,000+ companies)
│   ├── scripts/              # Migration, indexing, and backfill scripts
│   ├── tests/                # Pytest test suite
│   ├── Dockerfile            # Python 3.12-slim container
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # FilterSidebar, Header, JobCard, JobDetailPane, StatsStrip
│   │   ├── api/              # TanStack Query & Axios/fetch clients
│   │   └── App.jsx
│   ├── nginx.conf            # Production Nginx reverse proxy configuration
│   ├── Dockerfile            # Node 20 builder + Nginx production runner
│   └── package.json
└── docker-compose.yml        # Orchestrates frontend + backend stack
```

---

## 🐳 Quickstart with Docker Compose

Ensure Docker and Docker Compose are installed:

```bash
# 1. Clone repository
git clone https://github.com/ghanashyamauti/Collavio_JobScrapper.git
cd Collavio_JobScrapper

# 2. Configure environment (optional - defaults to local dev with SQLite fallback)
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Build and launch services
docker compose up --build -d
```

- **Frontend:** [http://localhost:5173](http://localhost:5173) or [http://localhost](http://localhost)
- **Backend API:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 💻 Local Development Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run migrations & start server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Run Tests

```bash
# Backend test suite
python -m pytest backend/tests -v

# Frontend build verification
cd frontend && npm run build
```

---

## 🔒 Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Neon Cloud or Supabase PostgreSQL connection string | SQLite fallback if empty |
| `FRONTEND_ORIGIN` | Allowed CORS origins | `http://localhost:5173` |
| `SYNC_INTERVAL_HOURS` | Background scraper frequency | `1` |
| `FALLBACK_SQLITE_FOR_LOCAL_DEV` | Automatic SQLite fallback for local test runs | `true` |

---

## 📄 License

MIT License. Designed and engineered for high-scale real-time job discovery.
