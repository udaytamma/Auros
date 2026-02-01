# Auros

Local-first AI job search tool for Principal/Senior TPM/PM roles.

See `auros.md` for the full delivery checklist.

## Features

- Playwright scraping of curated ATS platforms
- LLM extraction via Ollama (Qwen 2.5 Coder)
- Match scoring + Slack alerts (>= 0.70)
- Salary extraction + AI estimate with confidence gating
- React dashboard with charts and filtering
- Structured JSON logging with correlation IDs
- Prometheus metrics endpoint (/metrics)
- Rate limiting and CORS protection
- SQL injection protection on search queries

## Setup

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
cp .env.example .env
uvicorn api.main:app --reload --port 8008
```

Default port: **8008**

## Shared Ollama (Local LLM)
Ollama runs as a **separate local service** and can be reused by any project.

```bash
ollama serve
ollama pull qwen2.5-coder:7b
```

Set `OLLAMA_BASE_URL` in `.env` to point to the shared service (default `http://localhost:11434`).

If `OLLAMA_AUTO_START=true`, Auros will check Ollama on startup and attempt to run
`OLLAMA_START_COMMAND` if it's not already running (logs to `data/ollama-serve.log`).
To open Ollama in its own terminal on macOS, set:
`OLLAMA_START_COMMAND=osascript -e 'tell application "Terminal" to do script "ollama serve"'`

Health check:
```bash
./scripts/check-ollama.sh
```

### Frontend

The React UI is served directly from the API server (single-server architecture).

```bash
cd ui
npm install
npm run build
```

After building, the UI is available at http://localhost:8008.

For frontend development, rebuild after changes:
```bash
cd ui && npm run build
```

If API key is enabled, set `VITE_API_KEY` in `ui/.env` before building.

## Configuration

All settings are configured via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | LLM model for extraction |
| `OLLAMA_AUTO_START` | `true` | Auto-start Ollama on API boot if not running |
| `OLLAMA_START_COMMAND` | `ollama serve` | Command used to start Ollama |
| `OLLAMA_START_TIMEOUT` | `8` | Seconds to wait for Ollama after start |
| `SLACK_WEBHOOK_URL` | `None` | Slack webhook for notifications |
| `SLACK_MIN_SCORE` | `0.70` | Minimum score to trigger Slack alert |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/auros.db` | Database connection string |
| `SCAN_SCHEDULE_HOURS` | `6,12,18` | Hours to run scheduled scans (CT) |
| `SCAN_TIMEZONE` | `America/Chicago` | Timezone for scheduler |
| `DISABLE_SCHEDULER` | `false` | Disable automatic scanning |
| `SCRAPE_DELAY_MIN` | `5` | Minimum delay between page scrapes (seconds) |
| `SCRAPE_DELAY_MAX` | `10` | Maximum delay between page scrapes (seconds) |
| `MAX_CONCURRENT_PAGES` | `3` | Max concurrent browser pages |
| `PREFERRED_WORK_MODE` | `any` | Preferred work mode: any, remote, hybrid, onsite |
| `MIN_SALARY_CONFIDENCE` | `0.60` | Minimum confidence to display salary |
| `API_KEY` | `None` | Optional API key for authentication |
| `ATS_ALLOWED_DOMAINS` | See below | Allowed ATS domains for scraping |
| `CORS_ORIGINS` | `["http://localhost:8008", "http://localhost:4001"]` | Allowed CORS origins |
| `API_RATE_LIMIT_PER_MINUTE` | `60` | API rate limit per client IP |

**ATS_ALLOWED_DOMAINS default:** `greenhouse.io`, `boards.greenhouse.io`, `boards-api.greenhouse.io`, `lever.co`, `jobs.lever.co`, `api.lever.co`, `myworkdayjobs.com`, `workdayjobs.com`, `ashbyhq.com`, `rippling.com`, `jobs.jobvite.com`, `smartrecruiters.com`

**Production note:** For multi-user or higher concurrency, point `DATABASE_URL` to Postgres.

## API Endpoints

All endpoints require `X-API-Key` header if `API_KEY` is configured.

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/jobs` | List jobs with filtering (status, company_id, min_score, query, limit, offset) |
| `GET` | `/jobs/{job_id}` | Get single job details |
| `PATCH` | `/jobs/{job_id}/status` | Update job status |
| `GET` | `/jobs/export/csv` | Export all jobs as CSV |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search/trigger` | Trigger a manual scan |
| `GET` | `/search/status` | Get current scan status |

### Companies

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/companies` | List all companies |
| `PATCH` | `/companies/{company_id}` | Update company (enable/disable) |

### Stats

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stats` | Dashboard statistics (totals, by company, score buckets, daily trend) |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (db, ollama, slack status) |

### Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/metrics` | Prometheus metrics |

## Project Structure

```
Auros/
├── api/
│   ├── routers/          # API route handlers
│   │   ├── jobs.py       # Job CRUD with SQL injection protection
│   │   ├── search.py     # Scan trigger with task tracking
│   │   ├── companies.py  # Company management
│   │   ├── stats.py      # Dashboard statistics
│   │   ├── export.py     # CSV export
│   │   └── health.py     # Health checks
│   │   └── metrics.py    # Prometheus metrics
│   ├── services/         # Business logic
│   │   ├── pipeline.py   # Scan orchestration with ScanContext
│   │   ├── scraper.py    # Playwright scraping
│   │   ├── llm.py        # Ollama extraction
│   │   ├── salary.py     # Salary parsing/estimation
│   │   ├── scorer.py     # Match scoring
│   │   └── slack.py      # Notifications
│   ├── scheduler/        # APScheduler jobs
│   ├── config.py         # Pydantic settings
│   ├── logging.py        # Structured JSON logging
│   ├── main.py           # FastAPI app with middleware
│   ├── models.py         # SQLAlchemy models
│   └── schemas.py        # Pydantic schemas
├── ui/
│   └── src/
│       └── components/
│           ├── ErrorBoundary.tsx  # React error boundary
│           ├── FilterBar.tsx      # Job filtering UI
│           ├── JobTable.tsx       # Job listing
│           ├── BarChart.tsx       # Score distribution
│           └── LineChart.tsx      # Daily trend chart
├── tests/                # 135 tests
│   ├── unit/             # Unit tests (scorer, salary, scraper)
│   ├── integration/      # Integration tests
│   ├── system/           # System tests
│   └── e2e/              # End-to-end tests
├── alembic/              # Database migrations
└── scripts/              # Utility scripts
```

## Security Features

- **Rate Limiting:** Sliding window rate limiter (configurable per-minute limit)
- **CORS:** Configurable allowed origins
- **API Key Authentication:** Optional X-API-Key header validation
- **SQL Injection Protection:** User input escaped in LIKE queries
- **ErrorBoundary:** React error boundary for graceful UI failures

## Testing

```bash
source .venv/bin/activate
pytest tests/ -v
```

**Test coverage:** 135 tests across unit, integration, system, and e2e suites.

## CI Gate (Local)

```bash
./scripts/ci-check.sh
```

## Notes

- Salary is only displayed when confidence > 0.60
- Schedule defaults to 6am/12pm/6pm CT (configurable via `SCAN_SCHEDULE_HOURS`)
- Database migrations are managed via Alembic (`alembic/`)
- Structured logs are JSON-formatted with correlation IDs for tracing
