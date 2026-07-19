# Expenses Manager

A personal expense tracking app for individuals, households, and shared groups, built to track who paid, how costs are split, and provide expense statistics.

## Planned Features
### MVP

- User accounts
- Groups and members
- Manual expense entry
- Equal and exact splits
- Settlements and balance tracking
- Group categories
- Monthly, yearly, and YTD statistics
- Filters by person, category, date range, and necessity

### Later

- CSV import from Settle Up
- Multi-currency support
- Currency conversion API
- Android app
- Offline sync
- Bank and wallet integrations
- Automatic expense detection

## Tech Stack

- Backend: FastAPI
- Database: PostgreSQL
- Frontend: React + TypeScript (planned)
- Dev environment: Docker
- Testing: pytest
- Linting and formatting: Ruff

## Getting Started
### Prerequisites

- Python 3.14+
- uv
- Docker

### Local PostgreSQL

Copy `.env.example` to `.env`, then start PostgreSQL:

```bash
docker compose up -d
```

## Backend Development
Run backend commands from the `backend/` directory.

Install dependencies:

```bash
uv sync
```

Start the development server:

```bash
uv run fastapi dev
```
With the development server running, Swagger UI is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
Run tests:

```bash
uv run python -m pytest
```

Run lint and format checks:

```bash
uv run ruff check .
uv run ruff format --check --diff .
```
