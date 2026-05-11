# Stock Predictor

Stock Predictor is a FastAPI service for stock research, technical analysis, recommendation workflows, and evidence-backed research predictions. The project supports classic quote and analysis endpoints as well as a newer research layer that ties market data to source provenance, news-derived events, and AI infrastructure theme exposure.

## What this project does

- Serves stock quote, company, analysis, prediction, recommendation, and stock-list endpoints
- Exposes `GET /api/v1/stocks/{symbol}/research-prediction` for source-aware research output
- Exposes `GET /api/v1/themes/ai-infrastructure` for AI infrastructure and inference theme mapping
- Exposes `GET /api/v1/market/predictions/daily-report` for next-day verification and trend tracking
- Includes a source registry for free and low-cost market and news sources
- Supports local development with SQLite or a broader Docker setup with Postgres and Redis

## Prerequisites

### Required

| Requirement | Notes |
| --- | --- |
| Python 3.11+ | Docker uses Python 3.11 and the local repo currently uses a Python 3.12 virtualenv |
| `pip` | Used to install Python dependencies |
| Virtual environment support | `python3 -m venv venv` |

### Optional but useful

| Requirement | When you need it |
| --- | --- |
| Docker and Docker Compose | For the Postgres + Redis development stack |
| PostgreSQL | For non-SQLite local development |
| Redis | For broader app and background-task workflows |
| Polygon API key | For richer market data in the legacy data fetcher |
| NewsAPI key | For richer article ingestion in the legacy data fetcher |
| Alpha Vantage API key | Optional source expansion |

## Environment variables

The app defaults to `production` mode, so you should set development-friendly values before starting it locally.

| Variable | Required for local run | Example |
| --- | --- | --- |
| `ENVIRONMENT` | Yes | `development` |
| `SECRET_KEY` | Yes | `dev-secret-key` |
| `DEBUG` | Recommended | `true` |
| `DATABASE_URL` | Recommended | `sqlite+aiosqlite:///./stock_predictor_dev.db` |
| `REDIS_URL` | Optional for local API-only flows | `redis://localhost:6379` |
| `POLYGON_API_KEY` | Optional | `...` |
| `NEWS_API_KEY` | Optional | `...` |
| `ALPHA_VANTAGE_API_KEY` | Optional | `...` |
| `ENABLE_LOCAL_LLM` | Optional | `false` |
| `LOCAL_LLM_PROVIDER` | Optional | `ollama` |
| `LOCAL_LLM_BASE_URL` | Optional | `http://macmini2.local:11434/v1` |
| `LOCAL_LLM_MODEL` | Optional | `qwen3:4b` |
| `LOCAL_LLM_EMBEDDING_MODEL` | Optional | `nomic-embed-text` |
| `LOCAL_LLM_MAX_ANALYSES_PER_REPORT` | Optional | `2` |
| `ENABLE_SCENARIO_SWARM` | Optional | `true` |
| `SCENARIO_SWARM_MAX_IDEAS_PER_REPORT` | Optional | `3` |
| `SCENARIO_SWARM_AGENT_COUNT` | Optional | `4` |
| `HOST` | Optional | `127.0.0.1` |
| `PORT` | Optional | `8000` |

## Get started

### 1. Create or activate the virtual environment

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If the local `venv` already exists, you only need:

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
source venv/bin/activate
```

### 2. Choose your runtime shape

#### Scenario A: Single-machine local development

Use this when everything runs on one Mac and you only need browser access from that same machine.

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
source venv/bin/activate
export ENVIRONMENT=development
export SECRET_KEY=dev-secret-key
export DEBUG=true
export DATABASE_URL=sqlite+aiosqlite:///./stock_predictor_dev.db
export HOST=127.0.0.1
export PORT=8000
uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
```

#### Scenario B: Two-machine setup with Ollama on the network

Use this when:

- `macmini1.local` runs `stock_predictor`
- `macmini2.local` runs Ollama

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
source venv/bin/activate
export ENVIRONMENT=development
export SECRET_KEY=dev-secret-key
export DEBUG=true
export DATABASE_URL=sqlite+aiosqlite:///./stock_predictor_dev.db

export ENABLE_LOCAL_LLM=true
export LOCAL_LLM_PROVIDER=ollama
export LOCAL_LLM_BASE_URL=http://macmini2.local:11434/v1
export LOCAL_LLM_MODEL=qwen3:4b
export LOCAL_LLM_EMBEDDING_MODEL=nomic-embed-text
export LOCAL_LLM_TIMEOUT_SECONDS=60
export LOCAL_LLM_MAX_ANALYSES_PER_REPORT=2

export ENABLE_SCENARIO_SWARM=true
export SCENARIO_SWARM_MAX_IDEAS_PER_REPORT=3
export SCENARIO_SWARM_AGENT_COUNT=4

export HOST=127.0.0.1
export PORT=8000
uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
```

What this enables:

- deterministic event and evidence scoring
- structured local-model thesis review
- a small role-based scenario swarm
- daily snapshot storage and next-day validation
- CSV export with scenario columns for Excel or downstream analysis

#### Scenario C: LAN access from other devices on the same network

Use this when you want to open the app from another laptop, tablet, or desktop on the same Wi-Fi or wired network.

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
source venv/bin/activate
export ENVIRONMENT=development
export SECRET_KEY=dev-secret-key
export DEBUG=true
export DATABASE_URL=sqlite+aiosqlite:///./stock_predictor_dev.db
export HOST=0.0.0.0
export PORT=8000
uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
```

Then open this from another device:

```text
http://macmini1.local:8000/
```

If you prefer the helper script:

```bash
HOST=0.0.0.0 PORT=8000 ./start_dev.sh
```

#### Scenario D: Fastest script-based SQLite run

This is the easiest path when you want the existing helper script and same-machine access.

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
./start_dev.sh
```

What this script does:

- Sets `ENVIRONMENT=development`
- Sets `DEBUG=true`
- Uses `sqlite+aiosqlite:///./stock_predictor_dev.db`
- Starts Uvicorn on `http://127.0.0.1:8000`

#### Scenario E: Manual local run with your own environment

Use this when you want explicit control over config.

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
source venv/bin/activate
export ENVIRONMENT=development
export SECRET_KEY=dev-secret-key
export DEBUG=true
export DATABASE_URL=sqlite+aiosqlite:///./stock_predictor_dev.db
export HOST=127.0.0.1
export PORT=8000
uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
```

#### Scenario F: Docker-backed stack with Postgres and Redis

Use this when you want the app plus supporting services.

Before starting Docker Compose, create a local `.env` file so the app container does not boot with production defaults:

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
cat > .env <<'EOF'
ENVIRONMENT=development
SECRET_KEY=dev-secret-key
DEBUG=true
EOF
```

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
docker-compose up --build
```

The Docker stack starts:

- `app`
- `postgres`
- `redis`
- `celery`
- `celery-beat`

If you only want the API running locally, Scenario A is still the simpler path.

## First checks after startup

If you started with `DEBUG=true`, docs should be available.

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api
```

Useful local URLs:

- App root: `http://127.0.0.1:8000/`
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Access from other devices on the same network

If `ping macmini1.local` works but `http://macmini1.local:8000/` does not open in a browser, the most common reason is that the app is only listening on loopback.

Important detail:

- `ping macmini1.local` proving `10.0.0.5` works means mDNS name resolution is fine
- `nslookup macmini1.local` returning `NXDOMAIN` is expected on many networks because `.local` is usually resolved by mDNS, not by your normal DNS server

### Checklist

1. Start the app on `macmini1` with a LAN-visible bind:

```bash
HOST=0.0.0.0 PORT=8000 ./start_dev.sh
```

or:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Confirm the server is listening on all interfaces from `macmini1`:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Expected shape:

- good: `*:8000` or `0.0.0.0:8000`
- not enough for LAN: `127.0.0.1:8000`

3. Make sure macOS Firewall allows incoming connections for Python or Terminal:

- `System Settings` -> `Network` -> `Firewall`
- either turn Firewall off temporarily for testing, or allow incoming connections for the terminal app / Python runtime you are using

4. From another device on the same network, test:

```bash
curl http://macmini1.local:8000/health
curl http://macmini1.local:8000/api
```

If those work, the browser URL should also work:

```text
http://macmini1.local:8000/
```

5. If `.local` is flaky on a non-Apple client, test direct IP once:

```text
http://10.0.0.5:8000/
```

If the IP works but `.local` does not, the problem is mDNS support on that client, not the app.

### Recommended LAN run command for this project

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
source venv/bin/activate
export ENVIRONMENT=development
export SECRET_KEY=dev-secret-key
export DEBUG=true
export DATABASE_URL=sqlite+aiosqlite:///./stock_predictor_dev.db
export ENABLE_LOCAL_LLM=true
export LOCAL_LLM_PROVIDER=ollama
export LOCAL_LLM_BASE_URL=http://macmini2.local:11434/v1
export LOCAL_LLM_MODEL=qwen3:4b
export LOCAL_LLM_MAX_ANALYSES_PER_REPORT=2
export ENABLE_SCENARIO_SWARM=true
export SCENARIO_SWARM_MAX_IDEAS_PER_REPORT=3
export SCENARIO_SWARM_AGENT_COUNT=4
export HOST=0.0.0.0
export PORT=8000
uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
```

## Usage scenarios

### Scenario 1: Classic stock quote and recommendation flow

Use the existing stock endpoints when you want basic stock data and rule-based recommendations.

```bash
curl http://127.0.0.1:8000/api/v1/stocks/AAPL/quote
curl http://127.0.0.1:8000/api/v1/stocks/AAPL/company
curl http://127.0.0.1:8000/api/v1/stocks/AAPL/analysis
curl http://127.0.0.1:8000/api/v1/stocks/AAPL/recommendation
```

### Scenario 2: Evidence-backed research prediction

Use the research endpoint when you want probabilities, evidence cards, risk factors, and source provenance together.

```bash
curl http://127.0.0.1:8000/api/v1/stocks/NVDA/research-prediction
curl http://127.0.0.1:8000/api/v1/stocks/TSM/research-prediction
curl http://127.0.0.1:8000/api/v1/stocks/VRT/research-prediction
curl http://127.0.0.1:8000/api/v1/stocks/MSFT/research-prediction
```

Expect these response areas:

- `dataQuality`
- `sourceProvenance`
- `themeExposures`
- `events`
- `horizons`
- `riskFactors`
- `evidence`
- `disclaimer`

For ranked daily ideas, the market-intelligence feed now also attaches `supportingEvidence` links to each predicted stock when source URLs are available.

### Scenario 3: AI infrastructure and inference theme exploration

Use the theme endpoint to inspect second-order AI beneficiaries beyond GPU vendors.

```bash
curl http://127.0.0.1:8000/api/v1/themes/ai-infrastructure
```

The theme currently covers layers such as:

- GPU and accelerator vendors
- Foundry and manufacturing capacity
- Equipment and process control
- EDA and IP
- Memory and storage
- Networking
- Server integration
- Datacenter power and cooling
- Datacenter real estate
- Cloud AI platforms
- Agentic and inference software

### Scenario 4: Stock list generation

Use stock lists when you want ranked collections instead of single-symbol analysis.

```bash
curl "http://127.0.0.1:8000/api/v1/lists/all-time-high?max_items=10"
curl "http://127.0.0.1:8000/api/v1/lists/undervalued?symbols=AAPL,GOOGL,MSFT"
curl "http://127.0.0.1:8000/api/v1/lists/sp500"
```

### Scenario 5: Local research development without external API keys

The app can still run without market-data API keys:

- The local startup script uses SQLite, so you do not need Postgres just to boot the API
- Some services can fall back to demo or simplified data paths
- The research prediction layer includes source-quality metadata so responses can indicate mixed or degraded coverage

This is useful for UI work, contract checks, route wiring, and focused service development.

### Scenario 6: Daily prediction audit report

Use the daily report when you want to know whether yesterday's or last week's calls were actually working.

```bash
curl "http://127.0.0.1:8000/api/v1/market/predictions/daily-report?days=30"
```

The daily report includes:

- `overall` accuracy, pending count, and average benchmark-relative return
- `trend` status showing whether the recent window is improving or slipping
- `todayPredictions` with supporting evidence links
- `recentEvaluations` with realized return, benchmark return, and excess return
- `localModelPlan` showing the configured or planned local-analysis slot

This is the main answer to "are the predictions actually getting better?"

### Scenario 7: Local-model analysis and scenario swarm over the local network

The predictor now reserves a configuration slot for a local model that works from retrieved evidence instead of making unsupported claims. The intended flow is:

1. fetch fresh quote, filing, macro, and news evidence
2. rank and deduplicate evidence before prompting the model
3. ask the local model for a structured thesis, counter-thesis, and what changed today
4. store the model output beside the raw evidence so next-day review can audit both

Two easy local providers to target are [Ollama](https://docs.ollama.com/api/openai-compatibility) and [LM Studio](https://lmstudio.ai/docs/app/api/endpoints/openai).

Example for a two-machine setup where Ollama runs on `macmini2.local` and the API runs on another Mac:

```bash
export ENABLE_LOCAL_LLM=true
export LOCAL_LLM_PROVIDER=ollama
export LOCAL_LLM_BASE_URL=http://macmini2.local:11434/v1
export LOCAL_LLM_MODEL=qwen3:4b
export LOCAL_LLM_EMBEDDING_MODEL=nomic-embed-text
export LOCAL_LLM_MAX_ANALYSES_PER_REPORT=2
export ENABLE_SCENARIO_SWARM=true
export SCENARIO_SWARM_MAX_IDEAS_PER_REPORT=3
export SCENARIO_SWARM_AGENT_COUNT=4
```

In the current implementation:

- the market-intelligence report sends a small evidence bundle for the top ideas to the configured model
- the app stores the returned thesis with the daily snapshot as `localModelAnalysis`
- the app also runs a small role-based scenario swarm and stores that result as `scenarioSwarm`
- the CSV export now includes columns such as `scenario_verdict`, `scenario_support_score`, `scenario_disagreement_score`, and `scenario_fragility_score`

## Testing

### Focused research tests

This is the most reliable validation path for the new research work.

```bash
cd /Users/sandgupt/RandomIdeasWithAI/stock_predictor
SECRET_KEY=test-secret-key ENVIRONMENT=testing ./venv/bin/python -m pytest \
  tests/test_services/test_daily_prediction_report.py \
  tests/test_services/test_local_model_analysis.py \
  tests/test_services/test_research_platform.py \
  tests/test_services/test_market_intelligence.py \
  tests/test_api/test_research_routes.py \
  tests/test_api/test_market_routes.py \
  tests/test_services/test_data_fetcher.py -q
```

### Core service tests

```bash
make test
```

### Full suite

```bash
make test-all
```

Note: the broader test suite currently includes pre-existing failures outside the new research feature area, so use the focused research test command above when validating the research platform work.

## Helpful development commands

```bash
make dev
make lint
make format
make docker-up
make docker-down
```

## Project notes

- `make run-dev` assumes you already exported the required environment variables or created a suitable `.env`
- `/docs` and `/redoc` are only enabled when `DEBUG=true`
- The root route `/` serves the static web interface from `app/static/index.html`
- The API prefix for application routes is `/api/v1`

## Related docs

- Redesign notes: [STOCK_PREDICTOR_REDESIGN.md](/Users/sandgupt/RandomIdeasWithAI/stock_predictor/STOCK_PREDICTOR_REDESIGN.md)
- Speckit project: [spec.md](/Users/sandgupt/Wf-Adobe/spec-driven-development/projects/stock-predictor-research-platform/spec.md)
