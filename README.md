# WineTracker

Track the bottles in your cellar, the occasions you opened them, who you were with,
and how each bottle compared with your general opinion of the wine.

- **API:** FastAPI + SQLAlchemy 2 + MySQL 8 (shared by the web UI and the future mobile app)
- **Web UI:** Dash + Dash Mantine Components, English and Portuguese (Brazil), WCAG 2.2 AA
- **Ratings:** 0–10 wine glasses in half-glass steps

See [docs/PLAN.md](docs/PLAN.md) for product decisions, architecture and roadmap.

## Getting started

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows; use .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
cp .env.example .env            # then set WT_DATABASE_URL and the two secrets
```

Create the database on your MySQL instance, then apply migrations:

```sql
CREATE DATABASE winetracker CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

```bash
alembic upgrade head
```

Run the API and the web UI in two terminals:

```bash
uvicorn winetracker.api.main:app --reload --port 8000
python -m winetracker.web.app   # http://127.0.0.1:8050
```

API docs: http://127.0.0.1:8000/docs (disabled in production).

Without `WT_DATABASE_URL`, everything falls back to a local SQLite file for quick tries.

## Quality checks

```bash
ruff format --check src tests migrations && ruff check src tests migrations
mypy
pytest                                   # SQLite, fast
WT_TEST_DATABASE_URL=mysql+pymysql://user:pass@host/winetracker_test pytest   # real MySQL
```

CI runs all of the above, plus migrations up and down against MySQL 8.

## Layout

```
src/winetracker/
  domain/         enums and the Rating value object (no framework code)
  models/         SQLAlchemy ORM models (schema changes go through Alembic)
  repositories/   data access
  services/       business rules
  api/            FastAPI app, routers, request/response schemas
  web/            Dash UI: pages, components, i18n, theme
migrations/       Alembic migrations
tests/
```
