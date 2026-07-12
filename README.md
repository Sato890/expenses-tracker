# Expenses Manager

A personal expense tracking app for individuals, households, and shared groups, built to track who paid, how costs are split, and provide expense statistics.

## Current Status

MVP planning stage.

## Tech Stack

- Backend: FastAPI
- Database: PostgreSQL
- Frontend: React + TypeScript
- Dev environment: Docker
- Testing: pytest

## Project Goals

- Learn Python backend development with FastAPI
- Practice OOP and design patterns
- Build a usable app for tracking shared expenses

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

## Getting Started

This project will run locally first using Docker for the database and separate backend and frontend services.

### Local Database

Copy `.env.example` to `.env`, then start PostgreSQL:

```bash
docker compose up -d
```

### Prerequisites

- Python
- Node.js
- Docker
- Git


## Folder Structure

- `backend/`: FastAPI app, business logic, database models, and tests
- `frontend/`: React app and UI code
- `docker-compose.yml`: local development services
