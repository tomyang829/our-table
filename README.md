# Our Table

A personal recipe manager. Paste a URL from any recipe website, extract the recipe automatically, and save a personal copy you can edit however you like — adjust ingredients, rewrite instructions, add notes — while always keeping a link back to the original.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, TanStack Query, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, SQLAlchemy (async), Alembic, Pydantic |
| Database | PostgreSQL 16 |
| Auth | Google + GitHub OAuth (Authlib), JWT in httpOnly cookie |
| Scraping | recipe-scrapers (300+ sites + generic schema.org fallback) |
| Testing | pytest + respx (backend), Vitest + Testing Library + msw (frontend) |

## Features

- **Extract** — paste any recipe URL and pull out title, ingredients, and instructions automatically
- **Save & edit** — keep your own copy with per-step ingredient and instruction editing; the original is always preserved
- **Duplicate detection** — warns when you try to save a URL you've already saved
- **Delete** — remove recipes you no longer need
- **Compare with original** — view the scraped original alongside your edited version, with a link back to the source

## Project layout

```
our-table/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + router wiring
│   │   ├── core/              # config, database session, auth helpers
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── api/               # Route handlers (auth, recipes, users)
│   │   └── services/          # Business logic (recipe extractor)
│   ├── tests/                 # pytest integration + unit tests
│   ├── alembic/               # DB migrations
│   └── pyproject.toml         # Python deps (managed with uv)
├── frontend/
│   ├── src/
│   │   ├── pages/             # Route-level components + co-located tests
│   │   ├── components/        # Shared UI components
│   │   ├── hooks/             # React Query hooks
│   │   ├── api/               # Typed fetch wrappers
│   │   ├── mocks/             # msw handlers shared by tests and dev mode
│   │   └── types/             # Shared TypeScript types
│   └── package.json
├── docker-compose.yml         # Postgres + pgAdmin for local dev
├── docker-compose.test.yml    # Isolated test DB (port 5433)
└── Makefile                   # Convenience commands
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) — runs Postgres locally
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- Node.js 18+ and npm

## First-time setup

**1. Copy environment files**

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` and add your OAuth credentials if you want Google/GitHub login. The database URL and `SECRET_KEY=changeme` are fine for local development.

**2. Install frontend dependencies**

```bash
cd frontend && npm install
```

**3. Start Postgres and run migrations**

```bash
make dev-deps   # docker compose up -d
make migrate    # alembic upgrade head
```

## Running locally

Open two terminals:

```bash
make backend    # FastAPI on http://localhost:8000
make frontend   # Vite on http://localhost:5173
```

Open **http://localhost:5173**. The Vite dev server proxies all `/api/*` requests to the FastAPI backend, so no CORS configuration is needed.

### Skipping OAuth in development

Add `DEV_BYPASS_AUTH=true` to `backend/.env`. All API requests will be automatically authenticated as a local dev user (`dev@local.dev`) — no OAuth credentials or login step required.

The login page also shows a **"Dev Login (skip OAuth)"** button when running in dev mode that hits `GET /api/auth/dev-login`, sets a real session cookie, and redirects to the app.

## Running tests

```bash
make test
```

This spins up an isolated test database on port 5433, runs `pytest` and `vitest`, then tears the container down. The test database is separate from the dev database so tests never affect your local data.

Run just the backend or frontend tests independently:

```bash
cd backend && uv run pytest             # backend only
cd frontend && npm run test:run         # frontend only
```

## Key API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/recipes/extract` | Scrape a URL; returns source recipe + duplicate flag |
| `POST` | `/api/recipes/source/{id}/save` | Save a personal copy of a source recipe |
| `GET` | `/api/recipes/mine` | List the current user's saved recipes |
| `GET` | `/api/recipes/mine/{id}` | Fetch one recipe (includes original source) |
| `PUT` | `/api/recipes/mine/{id}` | Update title, ingredients, instructions, notes |
| `DELETE` | `/api/recipes/mine/{id}` | Delete a saved recipe |
| `GET` | `/api/users/me` | Current user profile |
| `GET` | `/api/auth/google` | Initiate Google OAuth flow |
| `GET` | `/api/auth/github` | Initiate GitHub OAuth flow |
| `GET` | `/api/auth/dev-login` | Dev-only instant login (requires `DEV_BYPASS_AUTH=true`) |

## Stopping

```bash
make down   # stops and removes Docker containers
```
