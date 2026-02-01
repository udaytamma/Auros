# Auros

AI-powered job search assistant for Principal TPM/PM roles. Automatically scrapes company career pages, extracts job details using LLM, scores matches, and sends Slack notifications for high-scoring opportunities.

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                     Auros System                        │
                    ├─────────────────────────────────────────────────────────┤
                    │  ┌─────────────┐     ┌─────────────┐     ┌───────────┐ │
  Browser ─────────►│  │   FastAPI   │────►│   Pipeline  │────►│  Ollama   │ │
   :8008            │  │  (API + UI) │     │  (Scraping) │     │  (LLM)    │ │
                    │  └─────────────┘     └─────────────┘     └───────────┘ │
                    │         │                   │                          │
                    │         ▼                   ▼                          │
                    │  ┌─────────────┐     ┌─────────────┐     ┌───────────┐ │
                    │  │   SQLite    │     │  Playwright │────►│  Career   │ │
                    │  │   (Data)    │     │  (Scraper)  │     │   Pages   │ │
                    │  └─────────────┘     └─────────────┘     └───────────┘ │
                    │                             │                          │
                    │                             ▼                          │
                    │                       ┌───────────┐                    │
                    │                       │   Slack   │                    │
                    │                       │  Webhook  │                    │
                    │                       └───────────┘                    │
                    └─────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Description |
|-----------|----------|-------------|
| FastAPI App | `api/main.py` | REST API with rate limiting, CORS, static file serving |
| Pipeline | `api/services/pipeline.py` | Orchestrates scraping, LLM extraction, scoring, notifications |
| Scraper | `api/services/scraper.py` | Playwright-based career page scraper with retry logic |
| Scorer | `api/services/scorer.py` | Weighted match scoring algorithm |
| Salary | `api/services/salary.py` | JD extraction + LLM estimation with confidence threshold |
| Logging | `api/logging.py` | Structured JSON logging with correlation IDs |
| Scheduler | `api/scheduler/jobs.py` | APScheduler for automated scans |
| React UI | `ui/src/` | Dashboard with filters, charts, job table |

---

## Database Schema

### Tables

#### companies
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | String | No | - | Primary key |
| name | String | No | - | Company display name |
| careers_url | String | No | - | URL to scrape |
| tier | Integer | No | `server_default="2"` | 1=Mag7, 2=Tier2, 3=Other |
| enabled | Boolean | No | `server_default=sa.true()` | Whether to include in scans |
| last_scraped | DateTime | Yes | null | Last successful scrape time |
| scrape_status | String | Yes | null | "success" or "failed" |

#### jobs
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | String | No | - | Primary key (UUID) |
| company_id | String | No | - | FK to companies.id |
| title | String | No | - | Job title |
| primary_function | String | Yes | null | Extracted function (TPM, PM, etc.) |
| url | String | No | - | Unique, indexed |
| yoe_min | Integer | Yes | null | Minimum years of experience |
| yoe_max | Integer | Yes | null | Maximum years of experience |
| yoe_source | String | Yes | null | "extracted" if parsed from JD |
| salary_min | Integer | Yes | null | Annual salary floor |
| salary_max | Integer | Yes | null | Annual salary ceiling |
| salary_source | String | Yes | null | "jd" or "ai" |
| salary_confidence | Float | Yes | null | 0.0-1.0 confidence score |
| salary_estimated | Boolean | No | `server_default=sa.false()` | True if AI-estimated |
| work_mode | String | Yes | null | "remote", "hybrid", "onsite", "unclear" |
| location | String | Yes | null | Job location |
| match_score | Float | Yes | null | 0.0-1.0 weighted score |
| raw_description | Text | Yes | null | Full job description text |
| status | String | No | `server_default="new"` | "new", "bookmarked", "applied", "hidden" |
| first_seen | DateTime | No | `server_default=sa.func.now()` | First discovery time |
| last_seen | DateTime | No | `server_default=sa.func.now()` | Most recent sighting |
| notified | Boolean | No | `server_default=sa.false()` | Whether Slack notification sent |

**Indexes:**
- `ix_jobs_company_status` on (company_id, status)
- `ix_jobs_url` on (url) - unique

#### scan_logs
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | String | No | - | Primary key (scan UUID) |
| started_at | DateTime | Yes | null | Scan start time |
| completed_at | DateTime | Yes | null | Scan end time |
| companies_scanned | Integer | Yes | null | Number of companies processed |
| jobs_found | Integer | Yes | null | Total jobs discovered |
| jobs_new | Integer | Yes | null | New jobs added |
| errors | Text | Yes | null | JSON array of error messages |

#### scan_state
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | String | No | - | Primary key (always "current") |
| status | String | No | `server_default="idle"` | "idle", "running", "completed" |
| started_at | DateTime | Yes | null | Current/last scan start |
| completed_at | DateTime | Yes | null | Last scan end |
| companies_scanned | Integer | Yes | null | Progress counter |
| jobs_found | Integer | Yes | null | Progress counter |
| jobs_new | Integer | Yes | null | Progress counter |
| errors | Text | Yes | null | JSON array of errors |

---

## Configuration

All settings are managed via environment variables or `.env` file using Pydantic Settings.

### Shared Ollama (Local LLM)
Ollama runs as a separate local service and can be shared across projects.

```bash
ollama serve
ollama pull qwen2.5-coder:7b
```

If `OLLAMA_AUTO_START=true`, Auros will check Ollama on startup and attempt to run
`OLLAMA_START_COMMAND` if it’s not already running (logs to `data/ollama-serve.log`).
To launch Ollama in its own terminal on macOS, set:
`OLLAMA_START_COMMAND=osascript -e 'tell application "Terminal" to do script "ollama serve"'`

Health check:
```bash
./scripts/check-ollama.sh
```

### Settings (api/config.py)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| **Ollama** |
| `OLLAMA_BASE_URL` | str | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | str | `qwen2.5-coder:7b` | Model for LLM extraction |
| `OLLAMA_AUTO_START` | bool | True | Auto-start Ollama on API boot if not running |
| `OLLAMA_START_COMMAND` | str | `ollama serve` | Command used to start Ollama |
| `OLLAMA_START_TIMEOUT` | int | 8 | Seconds to wait for Ollama after start |
| **Slack** |
| `SLACK_WEBHOOK_URL` | str \| None | None | Webhook for notifications |
| `SLACK_MIN_SCORE` | float | 0.70 | Minimum score for notification |
| **Database** |
| `DATABASE_URL` | str | `sqlite+aiosqlite:///./data/auros.db` | SQLAlchemy async URL |
| **Scheduler** |
| `SCAN_SCHEDULE_HOURS` | str | `6,12,18` | Comma-separated hours (24h) |
| `SCAN_TIMEZONE` | str | `America/Chicago` | Timezone for scheduler |
| `DISABLE_SCHEDULER` | bool | False | Disable auto-scan |
| **Rate Limiting (Scraper)** |
| `SCRAPE_DELAY_MIN` | int | 5 | Min seconds between page loads |
| `SCRAPE_DELAY_MAX` | int | 10 | Max seconds between page loads |
| `MAX_CONCURRENT_PAGES` | int | 3 | Max parallel page fetches |
| **Preferences** |
| `PREFERRED_WORK_MODE` | str | `any` | Filter: any\|remote\|hybrid\|onsite |
| `MIN_SALARY_CONFIDENCE` | float | 0.60 | Confidence gate for salary |
| **Security** |
| `API_KEY` | str \| None | None | Optional API key authentication |
| **ATS Domains** |
| `ATS_ALLOWED_DOMAINS` | list[str] | See below | Allowed external job board domains |
| **CORS** |
| `CORS_ORIGINS` | list[str] | `["http://localhost:8008", "http://localhost:4001"]` | Allowed origins |
| **API Rate Limiting** |
| `API_RATE_LIMIT_PER_MINUTE` | int | 60 | Requests per minute per IP |

**ATS_ALLOWED_DOMAINS default:**
```python
[
    "greenhouse.io",
    "boards.greenhouse.io",
    "boards-api.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "api.lever.co",
    "myworkdayjobs.com",
    "workdayjobs.com",
    "ashbyhq.com",
    "rippling.com",
    "jobs.jobvite.com",
    "smartrecruiters.com",
]
```

**Production note:** For multi-user or higher concurrency, point `DATABASE_URL` to Postgres.

---

## Pipeline & Scan Context

### ScanContext Dataclass

The `ScanContext` dataclass (`api/services/pipeline.py`) tracks per-scan state without global mutable state:

```python
@dataclass
class ScanContext:
    scan_id: str              # UUID for this scan
    started_at: datetime      # UTC start time
    companies_scanned: int = 0
    jobs_found: int = 0
    jobs_new: int = 0
    errors: list[str] = field(default_factory=list)
```

### Database-Backed Scan State

Scan state is persisted to the `scan_state` table to:
- Prevent concurrent scans (thread-safe DB check)
- Allow status polling from UI during long scans
- Survive process restarts

Key functions:
- `_is_scan_running(session)` - Check if scan in progress
- `_reset_scan_state(session, scan_id)` - Initialize new scan
- `_update_scan_state(session, ctx)` - Persist progress
- `_complete_scan_state(session, ctx)` - Mark scan complete

### run_full_scan Flow

1. Check if scan already running (return current status if so)
2. Generate unique `scan_id`, set correlation ID for logging
3. Initialize `ScanContext` and database state
4. Fetch all enabled companies
5. For each company:
   - Scrape career page (with retry)
   - Filter jobs by title keywords
   - For each potential match:
     - Skip if URL already exists
     - Extract job info via LLM
     - Extract/estimate salary
     - Compute match score
     - Save to database
     - Send Slack notification if score >= threshold
   - Update company `last_scraped` and `scrape_status`
6. Mark scan complete
7. Create `ScanLog` entry
8. Return final status

---

## Structured Logging

### Features (api/logging.py)

- **JSON Format**: All logs output as JSON with timestamp, level, logger, message
- **Correlation IDs**: 8-character UUID prefix for request/scan tracing
- **Context Variables**: Thread-safe correlation ID via `contextvars.ContextVar`
- **Structured Methods**: `info_structured()`, `warning_structured()`, `error_structured()`

### Example Output

```json
{
  "timestamp": "2025-01-15T14:30:00.123456+00:00",
  "level": "INFO",
  "logger": "auros",
  "correlation_id": "a1b2c3d4",
  "message": "scan_company_completed",
  "company": "Google",
  "jobs_found": 15
}
```

### Usage

```python
from ..logging import configure_logging, set_correlation_id

logger = configure_logging()
set_correlation_id(scan_id[:8])
logger.info_structured("scan_started", scan_id=scan_id)
```

---

## Observability (Metrics)

### Prometheus Metrics

Expose metrics at `GET /metrics`. Includes:
- HTTP request count/latency
- In-progress request gauge
- Scan totals and running gauge
- Scrape error count
- Jobs found/new counters

Example scrape:
```bash
curl http://localhost:8008/metrics
```

---

## Rate Limiting Middleware

### API Rate Limiting (api/main.py)

In-memory sliding window rate limiter per IP address:

```python
class RateLimitMiddleware:
    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)
```

- **Window**: 60 seconds sliding
- **Default**: 60 requests per minute per IP
- **Configurable**: Via `API_RATE_LIMIT_PER_MINUTE` setting
- **Response**: HTTP 429 with `{"detail": "Rate limit exceeded"}`

**Note**: For production multi-instance deployment, use Redis-based rate limiting instead.

### Scraper Rate Limiting

Random delay between page loads to avoid detection:
- `SCRAPE_DELAY_MIN` to `SCRAPE_DELAY_MAX` seconds
- `MAX_CONCURRENT_PAGES` for parallel fetch limit

---

## Retry Logic

### retry_async Utility (api/utils/retry.py)

```python
async def retry_async(
    func: Callable[[], Awaitable],
    exceptions: tuple[Type[BaseException], ...],
    attempts: int = 3,
    base_delay: float = 0.5,
) -> object
```

- **Exponential backoff**: `base_delay * attempt` seconds
- **Used by**: Scraper (Playwright errors), LLM calls (httpx errors)

---

## Scoring Algorithm

### Weights (api/services/scorer.py)

| Factor | Weight | Description |
|--------|--------|-------------|
| Title | 0.30 | Matches: principal, senior, staff, lead, tpm, technical program, program manager, product manager |
| Keywords | 0.25 | AI/platform terms: ai, ml, platform, infrastructure, sre, reliability, cloud, genai, llm, devops |
| YOE | 0.20 | Overlap with target range (8-15 years) |
| Company Tier | 0.15 | Tier 1=1.0, Tier 2=0.8, Tier 3=0.6 |
| Work Mode | 0.10 | Match against `PREFERRED_WORK_MODE` preference |

### Word Boundary Matching

All keyword matching uses compiled regex with word boundaries to avoid false positives:
```python
pattern = r"\b" + re.escape(kw).replace("\\ ", r"\s+") + r"\b"
```

---

## Salary Extraction

### Two-Stage Approach (api/services/salary.py)

1. **JD Extraction**: Regex patterns for common salary formats
   - `$150,000 - $200,000`
   - `150k-200k`
   - `$150k-$200k`
   - Returns confidence 0.9

2. **LLM Estimation**: Fallback when JD extraction fails
   - Uses Ollama model
   - Returns confidence 0.0-1.0 based on model assessment

### Confidence Gate

```python
def apply_confidence_threshold(salary_tuple):
    if confidence < settings.MIN_SALARY_CONFIDENCE:  # 0.60
        return None
    return salary_tuple
```

Salaries below the confidence threshold are omitted from the job record.

---

## API Schemas

### Enums (api/schemas.py)

```python
class JobStatus(str, Enum):
    new = "new"
    bookmarked = "bookmarked"
    applied = "applied"
    hidden = "hidden"

class WorkMode(str, Enum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"
    unclear = "unclear"

class SalarySource(str, Enum):
    jd = "jd"
    ai = "ai"

class ScanStatus(str, Enum):
    idle = "idle"
    running = "running"
    completed = "completed"
```

### Response Models

- `CompanyOut` - Company details with scrape status
- `JobOut` - Full job record
- `JobListOut` - Paginated job list with total count
- `ScanStatusOut` - Current scan state
- `StatsOut` - Dashboard statistics

---

## Frontend

### React App (ui/src/)

- **Framework**: React with TypeScript
- **Build**: Vite
- **Styling**: Plain CSS (no framework)

### ErrorBoundary (ui/src/components/ErrorBoundary.tsx)

React class component that catches JavaScript errors in child component tree:

```tsx
export default class ErrorBoundary extends Component<Props, State> {
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="card">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>Reload Page</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

### Dashboard Features

- Stats cards (Total, New, Bookmarked, Applied, Hidden)
- Charts: Jobs by company, Score distribution, New jobs by day
- Filter bar: Status, Company, Min Score, Search query
- Job table with status update actions

---

## Testing

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_salary.py       # 28 tests - salary extraction
│   ├── test_scorer.py       # 40 tests - match scoring
│   └── test_scraper.py      # 39 tests - scraper logic
├── integration/
│   └── test_api.py          # 25 tests - API endpoints + DB
├── system/
│   └── test_pipeline.py     # 1 test - full pipeline mock
├── e2e/
│   └── test_api_e2e.py      # 1 test - root + health
└── gui/
    └── test_dashboard_ui.py # 1 test - Playwright UI test
```

**Total: 136 tests** across unit, integration, system, e2e, and gui categories.

### Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/gui/

# With coverage
pytest --cov=api --cov-report=term-missing
```

---

## Shared Utilities

### safe_json_parse (api/utils/json.py)

Robust JSON parsing that handles LLM responses with extra text:

```python
def safe_json_parse(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Extract JSON object from surrounding text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
```

---

## Quick Commands

```bash
# Start server (serves both API and UI)
cd /Users/omega/Projects/Auros
source .venv/bin/activate
uvicorn api.main:app --reload --port 8008

# Rebuild UI after frontend changes
cd /Users/omega/Projects/Auros/ui
npm run build

# Run tests
pytest

# Run migrations
alembic upgrade head
```

---

## Delivery Checklist

### Core Functionality
- [x] Scrape runs end-to-end for default company list
- [x] Job extraction works for title, location, work mode, YOE
- [x] Match scoring computed and saved
- [x] Salary extraction from JD works; AI estimation used only when needed
- [x] Salary confidence gate enforced (omit salary if &lt;= 0.60)
- [x] Slack notifications only for score >= threshold
- [x] Manual scan endpoint works
- [x] API endpoints return correct schema and pagination
- [x] UI loads from port 8008 and renders dashboard correctly

### Reliability & Resilience
- [x] Replace broad `except Exception` with specific exceptions + retry
- [x] Retry network/LLM/scraper calls with backoff
- [x] Playwright browser lifecycle managed via context managers
- [x] Scan state persisted to DB (not just memory)
- [x] Scrape health fields updated (`last_scraped`, `scrape_status`)

### Observability
- [x] Structured logging via Python `logging`
- [x] Log scan start/stop + per-company results + errors
- [x] Health endpoint returns DB + Ollama + Slack status

### Data & Migrations
- [x] Alembic migrations in place and runnable
- [x] Initial migration includes all tables + indexes
- [x] Migration bootstraps cleanly on existing DB

### Security
- [x] API key authentication supported (optional)
- [x] UI supports sending API key header
- [x] API rate limiting middleware (60 req/min per IP)

### Correctness & Quality
- [x] Word-boundary keyword matching to avoid false positives
- [x] `safe_json_parse` extracted to shared utility
- [x] Pydantic enums/validators for all enum fields
- [x] TypeScript interfaces for all API responses

### Testing (136 tests)
- [x] Unit tests: scorer (40), salary extraction (28), scraper (39)
- [x] Integration tests: API endpoints and DB seed (25)
- [x] System tests: pipeline with mocked scraper/LLM (1)
- [x] E2E tests: root + health (1)
- [x] GUI tests: dashboard renders via Playwright (1)
- [x] Minimum 80% test pass rate

### Deployment & Ops
- [x] Server runs on port 8008
- [x] UI build served from API root
- [x] `.env.example` updated for all configs
- [x] README updated with run + build + API key instructions

### Verification Steps
```bash
curl http://127.0.0.1:8008/       # Returns HTML (or JSON if UI not built)
curl http://127.0.0.1:8008/api    # Returns JSON
pytest                             # Tests pass
npm run build                      # UI builds successfully
```

---

## Future Enhancements

- [ ] Add caching for company scrape results
- [ ] Add pagination + search on UI table
- [ ] Add per-company scraper adapters (Greenhouse/Lever/Workday)
- [ ] Add richer analytics (conversion, streaks, pipeline stages)
- [ ] Redis-based rate limiting for multi-instance deployment
