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

Open `android/` in Android Studio and let Gradle sync complete. Use Java 21
and Android SDK 36.1. Keep `local.properties` and local SDK paths out of version control.

The configured API base URL is `http://127.0.0.1:8000`, defined by the
`API_BASE_URL` buildConfigField in `android/app/build.gradle.kts`. This slice
targets local development; deployed backend configuration comes later.
HTTP access is allowed only for `127.0.0.1` in debug builds.

To run on a physical phone:

1. Start FastAPI using the backend instructions above.
2. Enable USB debugging on the phone, connect a USB data cable, and approve
   the debugging prompt.
3. Run `adb reverse tcp:8000 tcp:8000` on the PC. This forwards the phone's
   port 8000 to the backend's port 8000 on the PC.
4. Select the phone in Android Studio and click Run.

The forwarding rule is not needed before every app launch. After reconnecting
or restarting the device or ADB, check `adb reverse --list` and recreate the
rule if it is missing.

Run checks from `android/` with Java 21 configured in `JAVA_HOME`:

```powershell
.\gradlew.bat assembleDebug testDebugUnitTest lintDebug
```

On macOS or Linux, use `bash ./gradlew` with the same tasks.
