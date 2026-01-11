# Knowledge & Metrics Service

A FastAPI backend service for evaluating alternative data vendors. Built for an investment team to explore historical performance metrics and query vendor behavior using natural language.

## Features

- **Vendor Metrics API**: Comprehensive statistics per vendor (signal strength, volatility, drawdowns)
- **Natural Language Queries**: Ask questions like "Compare all vendors" or "Show drawdowns for AlphaSignals"
- **Statistical Analysis**: Mean, std, correlation, coefficient of variation using pandas
- **Docker Ready**: Single `docker-compose up` to run everything
- **Type-Safe**: Full Pydantic models with OpenAPI documentation

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Create .env file with your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Build and run
docker-compose up --build

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Option 2: Local Development

#### Prerequisites

This project uses a `.python-version` file to specify the required Python version (3.11.4).

**1. Install pyenv (Python version manager)**

```bash
# macOS (using Homebrew)
brew install pyenv

# Add to shell config
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc
```

> For Linux/Windows, see [pyenv installation docs](https://github.com/pyenv/pyenv#installation)

**2. Install the required Python version**

```bash
# Install Python 3.11.4 (reads from .python-version automatically)
pyenv install 3.11.4

# Verify (should show 3.11.4 when in project directory)
python --version
```

**3. Install uv (fast Python package manager)**

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using Homebrew
brew install uv

# Verify installation
uv --version
```

**4. Set up environment variables**

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your OPENAI_API_KEY
```

#### Setup & Run

```bash
# Clone and navigate to project
cd knowledge-metrics-service

# Install dependencies (uv reads .python-version and pyproject.toml)
uv sync

# Run the API
uv run uvicorn app.main:app --reload

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## API Endpoints

### Metrics Endpoints (`/api/v1/metrics`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/info` | GET | Dataset metadata (vendors, date range, record count) |
| `/upload` | POST | Upload a CSV file to replace the dataset |
| `/vendors/{vendor}` | GET | Comprehensive metrics for a vendor |
| `/period` | GET | Aggregated metrics for a time period |
| `/compare` | GET | Comparative analysis and rankings |
| `/drawdowns` | GET | Drawdown/stress period analysis |

### Query Endpoints (`/api/v1/query`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | Submit a natural language query |
| `/query/supported` | GET | List supported query patterns |

### Example Queries

```bash
# Get metrics for a specific vendor
curl http://localhost:8000/api/v1/metrics/vendors/AlphaSignals

# With date filtering
curl "http://localhost:8000/api/v1/metrics/vendors/AlphaSignals?start_date=2020-01-01&end_date=2020-01-31"

# Compare all vendors
curl http://localhost:8000/api/v1/metrics/compare

# Natural language query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Which vendor has the best signal strength?"}'
```

## Test Scripts

Instead of a frontend, Python test scripts demonstrate API usage:

```bash
# Run all integration tests
python scripts/run_tests.py

# Test metrics endpoints (with detailed output)
python scripts/test_metrics.py

# Test natural language queries
python scripts/test_queries.py

# Against a different host
python scripts/test_metrics.py --base-url http://localhost:8000
```

## Project Structure

```
knowledge-metrics-service/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── api/
│   │   └── v1/routes/          # API endpoints
│   │       ├── metrics.py
│   │       └── queries.py
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── exceptions.py       # Custom exception classes
│   │   └── logging.py          # Logging configuration
│   ├── middleware/
│   │   ├── logging.py          # Request/response logging
│   │   └── request_id.py       # Request ID tracking
│   ├── models/                 # Pydantic models
│   │   ├── base.py
│   │   ├── metrics.py
│   │   ├── query.py
│   │   └── vendor.py
│   └── services/
│       ├── data_loader.py      # CSV loading & caching
│       ├── metrics_service.py  # Statistical computations
│       └── query_service.py    # NL query parsing
├── data/
│   └── vendor_metrics.csv      # Sample data (for demo)
├── scripts/                    # Test client scripts
├── tests/                      # Pytest test files
├── pyproject.toml              # Dependencies (PEP 621)
├── .pre-commit-config.yaml     # Pre-commit hooks config
├── Dockerfile
└── docker-compose.yml
```

## Design Decisions

### 1. Service Layer Pattern
Routes are thin controllers; business logic lives in services. This enables:
- Unit testing without HTTP
- Reuse across CLI/batch jobs
- Clear separation of concerns

### 2. LLM-Powered Query Parsing
Natural language queries are parsed using OpenAI with structured JSON output:
- Single LLM call extracts both intent and entities
- Handles query variations naturally
- Deterministic output via `temperature=0`

### 3. Singleton Data Loader
CSV is loaded once and cached. For this small, static dataset:
- Avoids repeated I/O
- Simple invalidation (restart service)
- Easy to extend to database/API sources

### 4. Dataclasses for Internal Models
Internal service models use `@dataclass` for simplicity; Pydantic models at API boundary for validation.

## Metrics Computed

| Metric | Description |
|--------|-------------|
| `signal_strength_mean/std/min/max` | Signal strength statistics |
| `feature_xy_correlation` | Correlation between feature_x and feature_y |
| `signal_volatility` | Coefficient of variation (std/mean) |
| `drawdown_rate` | % of periods in drawdown |
| `avg_signal_during_drawdown` | Signal behavior during stress |
| `ranking_by_avg_signal` | Vendor ranking by average signal strength |
| `ranking_by_stability` | Vendor ranking by stability (lower volatility = better) |

## Data

A sample CSV (`data/vendor_metrics.csv`) is included for demo purposes. To use your own data, replace it with a CSV matching this format:

```csv
vendor,date,universe,feature_x,feature_y,signal_strength,drawdown_flag
AlphaSignals,2020-01-03,Equities,0.12,-0.05,0.35,0
```

| Column | Type | Description |
|--------|------|-------------|
| `vendor` | string | Vendor/provider name |
| `date` | YYYY-MM-DD | Observation date |
| `universe` | string | Asset class (Equities, FX, Macro, etc.) |
| `feature_x` | float | Feature value |
| `feature_y` | float | Feature value |
| `signal_strength` | float | Signal strength metric |
| `drawdown_flag` | 0/1 | Whether period is in drawdown |

## Requirements

- Python 3.11+ (tested with 3.11.4)
- [uv](https://docs.astral.sh/uv/)
- Dependencies: FastAPI, Pydantic, pandas, NumPy, httpx, openai

## Development

```bash
# Install dependencies (using uv - recommended)
uv sync

# Install with dev dependencies (pytest, ruff)
uv sync --dev

# Run with auto-reload
uv run uvicorn app.main:app --reload

# View OpenAPI docs
open http://localhost:8000/docs

# Run tests
uv run pytest

# Run linter
uv run ruff check .
```

### Dependency Management

This project uses `pyproject.toml` (PEP 621) as the source of truth for dependencies:

```bash
# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Update all dependencies
uv lock --upgrade && uv sync
```

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run automated checks before each commit:

```bash
# Install pre-commit (already in dev dependencies)
uv sync --dev

# Install the git hooks
pre-commit install

# Run on all files (one-time check)
pre-commit run --all-files
```

**Configured hooks:**

| Hook | Purpose |
|------|---------|
| **pre-commit-hooks** | Trailing whitespace, end-of-file fixer, YAML/TOML validation |
| **ruff** | Fast linting + formatting (replaces flake8, isort, black) |

## License

Internal use only.
