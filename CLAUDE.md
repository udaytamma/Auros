# Auros - Project Instructions

> AI-powered job search tool for Principal/Senior TPM/PM roles.

## Servers & Ports

| Service | Command | Port | URL |
|---------|---------|------|-----|
| **Auros** | `uvicorn api.main:app --reload --port 8008` | 8008 | http://localhost:8008 |
| **Ollama** | `ollama serve` | 11434 | http://localhost:11434 |

**Single-server architecture:** FastAPI serves both API endpoints and the React UI from `/ui/dist`.

## Quick Start

```bash
source .venv/bin/activate

# Start server (serves both API and UI)
uvicorn api.main:app --reload --port 8008

# Rebuild UI after frontend changes
cd ui && npm run build

# Run tests
pytest tests/ -v

# TypeScript check
cd ui && npx tsc --noEmit
```

## Project Structure

```
Auros/
├── api/                            # FastAPI backend
│   ├── main.py                     # App with rate limiting, CORS
│   ├── config.py                   # 17 settings via Pydantic
│   ├── models.py                   # SQLAlchemy models
│   ├── logging.py                  # Structured logging + correlation IDs
│   ├── routers/                    # API endpoints
│   └── services/                   # Business logic
├── ui/                             # React frontend
│   ├── src/components/             # Including ErrorBoundary
│   └── src/pages/Dashboard.tsx     # Main view
├── alembic/                        # Database migrations
├── tests/                          # 135 tests
└── data/                           # SQLite database
```

## Configuration

All settings in `api/config.py`. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API |
| `OLLAMA_MODEL` | `qwen3:8b` | LLM model |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/auros.db` | Database |
| `API_KEY` | None | Optional auth |
| `CORS_ORIGINS` | `["http://localhost:5173", "http://localhost:4001"]` | Allowed origins |
| `API_RATE_LIMIT_PER_MINUTE` | 60 | Rate limit |
| `ATS_ALLOWED_DOMAINS` | See config.py | Allowed job boards |

## Key Implementation Details

### Security Features
- **SQL injection protection:** `_escape_like_pattern()` in `api/routers/jobs.py`
- **Rate limiting:** `RateLimitMiddleware` in `api/main.py` (sliding window)
- **CORS:** Configurable origins via `CORS_ORIGINS`
- **API key auth:** Optional via `API_KEY` setting

### Scan Pipeline
- **ScanContext dataclass:** Per-scan state in `api/services/pipeline.py`
- **Database-backed state:** No global mutable state, prevents race conditions
- **Task tracking:** Background tasks tracked in `api/routers/search.py`

### Logging
- **Structured JSON:** `api/logging.py` with `StructuredLogger`
- **Correlation IDs:** Track requests across the pipeline
- **Methods:** `info_structured()`, `warning_structured()`, `error_structured()`

### Frontend
- **ErrorBoundary:** Wraps Dashboard in `ui/src/App.tsx`
- **Stable filter key:** `useMemo` in `ui/src/hooks/useJobs.ts`
- **Type safety:** `JobFilters` interface in `ui/src/types/api.ts`

## Testing

```bash
# All tests (135 total)
pytest tests/ -v

# By category
pytest tests/unit/ -v          # 107 tests
pytest tests/integration/ -v   # 25 tests
pytest tests/e2e/ -v           # 1 test
pytest tests/gui/ -v           # 1 test
pytest tests/system/ -v        # 1 test
```

## Database

```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/jobs` | List with filters (status, company_id, min_score, query) |
| `GET` | `/jobs/{id}` | Job details |
| `PATCH` | `/jobs/{id}/status` | Update status |
| `POST` | `/search/trigger` | Start scan |
| `GET` | `/search/status` | Scan progress |
| `GET` | `/companies` | List companies |
| `PATCH` | `/companies/{id}` | Toggle enabled |
| `GET` | `/stats` | Dashboard statistics |
| `GET` | `/health` | System health |

## Documentation

- `README.md` - Setup and configuration
- `auros.md` - Full technical reference
- `.env.example` - All settings documented
