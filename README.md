# Expenses Manager

A personal expense tracking app for individuals, households, and shared groups, built to track who paid, how costs are split, and provide expense statistics.

### Stack
- Backend: FastAPI
- Database: PostgreSQL
- Local infrastructure: Docker
- Testing: pytest
- Linting and formatting: Ruff
## Getting Started

### Prerequisites

- Python 3.14+
- uv
- Docker

### Local PostgreSQL

From the repository root, copy `.env.example` to `.env`. It defines `DATABASE_URL` for development and `TEST_DATABASE_URL` for automated tests.

Start both PostgreSQL services:

```bash
docker compose up -d
```

## Backend Development

Run backend commands from the `backend/` directory.

Install dependencies:

```bash
uv sync --locked --dev
```

Create the database schema, then seed development data:
```bash
uv run alembic upgrade head 
uv run python -m app.adapters.seed
```

The repeatable seed adds the development group, participants, and built-in category catalog without duplicating seed data or replacing existing rows.

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

## Android Development

The `android/` directory contains the Kotlin and Jetpack Compose starter app.
Open this directory in Android Studio and let Gradle sync complete. The current
app displays the template greeting; API connectivity and financial screens are
not implemented yet.

The project uses Gradle 9.4.1, Android Gradle Plugin 9.2.1, Kotlin Compose plugin
2.2.10, and a Java 21 Gradle daemon. Install Android SDK Platform 36.1 through
SDK Manager. Minimum supported Android version is Android 7.0 (API 24).
Keep `local.properties` and local SDK paths out of version control.

From `android/`, run the Windows checks with a valid JDK configured in `JAVA_HOME`:

```powershell
.\gradlew.bat assembleDebug testDebugUnitTest lintDebug
```

On macOS or Linux, use `bash ./gradlew` with the same tasks.
The generated tests are template smoke checks, not financial behavior tests.

To run on a physical phone, enable USB debugging, connect a USB data cable,
approve the debugging prompt, select the phone in Android Studio, and click Run.
A physical-phone launch has been verified during initial setup.
