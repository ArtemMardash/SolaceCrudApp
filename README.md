# Users CRUD API — Containerized with Docker

A simple REST API for managing users (create, read, update, delete), built with **FastAPI** and **PostgreSQL**, and containerized with **Docker** and **Docker Compose**.

The only thing needed to run it is Docker Desktop — no local Python or PostgreSQL installation required.

---

## Process

1. **Built the app and ran it locally** against my local PostgreSQL, to make sure everything worked before involving Docker.
2. **Wrote the Dockerfile and tested the image on its own.** I ran the container against my local PostgreSQL (using `DB_HOST=host.docker.internal`), so I could confirm the image worked before adding more moving parts.
3. **Added `.dockerignore`** and checked what actually ended up inside the image (e.g. confirming `.env` wasn't copied in).
4. **Added Docker Compose** to run PostgreSQL in a container next to the app, with a healthcheck so the app waits for the database to be ready.
5. **Tested the full setup:** all endpoints through `/docs`, data surviving a `docker compose down` / `up`, and logs showing up in Docker Desktop.

---

## Tech stack

- Python 3.12
- FastAPI + Uvicorn
- SQLModel (SQLAlchemy + Pydantic)
- PostgreSQL 13.10
- Docker, Docker Compose

---

## Project structure

```
SolaceCrudApp/
├── user.py              # Entity: User table + validated request model
├── user_service.py      # Business logic + database access (CRUD, DB/table creation)
├── main.py              # Controller: FastAPI endpoints, logging setup
├── requirements.txt     # Pinned Python dependencies
├── Dockerfile           # How the app image is built
├── .dockerignore        # Files excluded from the image
├── docker-compose.yml   # Runs the app + PostgreSQL together
├── .env.example         # Template for environment variables
└── test_main.http       # Ready-made HTTP requests for testing
```

The app is intentionally kept to three layers: **Entity → Service → Controller**.

---

## How to run

1. Create your environment file from the template and set a password:
   ```
   cp .env.example .env
   ```
2. Build and start everything:
   ```
   docker compose up --build
   ```
3. Open the interactive API docs: **http://localhost:8000/docs**

Useful commands:

| Command | What it does |
|---|---|
| `docker compose up --build` | Build the image and start both containers |
| `docker compose down` | Stop and remove containers (data is kept) |
| `docker compose down -v` | Also delete the database volume (fresh start) |
| `docker compose logs -f app` | Follow the app's logs |

### Environment variables

| Variable | Description | Example |
|---|---|---|
| `DB_HOST` | Database host (overridden to `postgres.db` in Compose) | `localhost` |
| `DB_PORT` | Database port (overridden to `5432` in Compose) | `5432` |
| `DB_NAME` | Database name (created automatically if missing) | `users_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `change_me` |
| `LOG_LEVEL` | Optional: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

---

## API endpoints

| Method | Path | Description | Success |
|---|---|---|---|
| POST | `/users` | Create a user | 201 |
| GET | `/users` | List all users | 200 |
| GET | `/users/{id}` | Get one user | 200 / 404 |
| PUT | `/users/{id}` | Update a user (all fields) | 200 / 404 |
| DELETE | `/users/{id}` | Delete a user | 204 / 404 |

Example request body:

```json
{
  "name": "John Doe",
  "age": 30,
  "dob": "1995-04-12",
  "location": "Berlin",
  "work": "Engineer"
}
```

---

## Architecture

```
  Your machine
  ─────────────────────────────────────────────────────────────
   Browser / Postman              DB tool (optional)
        │ localhost:8000                │ localhost:5433
        ▼                               ▼
  ┌─────────────── Docker Compose network ───────────────────┐
  │                                                          │
  │   ┌──────────────┐   postgres.db:5432   ┌─────────────┐  │
  │   │     app      │ ───────────────────► │ postgres.db │  │
  │   │ FastAPI:8000 │                      │ Postgres 13 │  │
  │   └──────────────┘                      └──────┬──────┘  │
  │                                                │         │
  └────────────────────────────────────────────────┼─────────┘
                                                   ▼
                                     volume: postgres-data
                                     (data survives restarts)
```

- **app** — built from the `Dockerfile`.
- **postgres.db** — the official `postgres:13.10` image; no custom Dockerfile needed.
- The containers talk over Compose's private network, where each service's **name is its hostname**.
- The database is also published on port **5433** for connecting with a DB tool, avoiding a clash with a local PostgreSQL on 5432.

---

## Decisions

**Base image: `python:3.12-slim`**
I pinned the Python version to match my local setup instead of using `python:latest`, so a rebuild in the future can't silently switch Python versions. The slim variant keeps the final image at about **180 MB**, while the full Python image alone is around 1 GB. I avoided Alpine because Python packages with compiled parts (like the PostgreSQL driver) often don't install cleanly there.

**PostgreSQL 13.10**
I used the same version I run locally, to keep behaviour consistent between local development and the container. (Note: PostgreSQL 13 stopped getting updates in November 2025, so upgrading would be a sensible next step.)

**Layer caching: requirements first, code second**
The Dockerfile copies `requirements.txt` and installs dependencies *before* copying the code. Docker caches each step, so when only the code changes, the dependency install is reused and rebuilds take seconds.

**`COPY . .` + `.dockerignore`**
I first listed each file explicitly (`COPY main.py .`, etc.), which is safe but means every new file must be added by hand. I switched to `COPY . .` and use `.dockerignore` to exclude `.env`, `.venv/`, `__pycache__/`, `.idea/` and other files the app doesn't need. I verified that `.env` is not inside the image.

**Secrets stay out of the image**
Database credentials live only in `.env` (which is not committed and not copied into the image). Compose passes them in when the containers start via `env_file` and `${...}` substitution. The compose file has no passwords written in it. `.env.example` documents the variables without real values.

**Healthcheck + `depends_on: condition: service_healthy`**
`depends_on` on its own only waits for the Postgres *container* to start, not for Postgres to be *ready* to accept connections. A healthcheck using `pg_isready` makes the app wait until the database is actually ready, preventing "connection refused" errors on startup.

**The app creates its own database**
On startup the app checks whether the database exists and creates it if not, then creates the table. This means it works on a fresh PostgreSQL anywhere (local or container) without manual setup.
*Tradeoff:* it's convenient, but the database user needs permission to create databases. In production, you'd usually create the database separately and give the app a user with fewer permissions.

**Logging to stdout**
The app logs to the console (e.g. `Created user id=1`, `User id=99 not found`) with a level controlled by `LOG_LEVEL`. This is the standard Docker approach: Docker collects container output, so logs are visible in Docker Desktop and via `docker compose logs`.

---

## Challenges and how I solved them

**1. The database didn't exist on first run**
The app connected to PostgreSQL successfully but crashed on startup with `database "users_db" does not exist`. The app created its tables automatically, but not the database itself, so every fresh environment (a new machine, a new container, a wiped volume) needed a manual setup step.
*Solution:* I added a startup step that connects to PostgreSQL's built-in `postgres` database, checks `pg_database`, and runs `CREATE DATABASE` only if it's missing. One detail: PostgreSQL doesn't allow `CREATE DATABASE` inside a transaction, so this connection runs in autocommit mode. Now the app sets itself up on any empty PostgreSQL server, which is exactly what a container needs.

**2. The app could start before the database was ready**
`depends_on` in Docker Compose only waits for the database *container* to start, not for PostgreSQL inside it to be ready. PostgreSQL needs a few seconds to initialise, especially on the first run, when it creates its data files. So the app could try to connect too early and fail with "connection refused".
*Solution:* I added a healthcheck to the database service using `pg_isready`, and set the app to `depends_on: condition: service_healthy`. Compose now starts the app only once PostgreSQL actually accepts connections.

**3. Refreshing Docker syntax**
I hadn't used Docker in a while, so I didn't remember all the Dockerfile and Compose syntax off the top of my head and had to look some of it up again as I went. To catch mistakes early, I validated the Compose file with `docker compose config` before running it, and checked the built image's contents directly instead of assuming they were right.

---

## What I'd improve next

- **Run the app as a non-root user** inside the container — right now it runs as root, which is a security risk if the app were ever compromised.
- **Upgrade PostgreSQL** to a supported version (16 or 17), since 13 no longer gets security updates.
- **Add automated tests** for the endpoints, so changes can be checked without testing by hand.
- **Use database migrations (Alembic)** instead of creating tables on startup — right now, changing a column on an existing table would need to be done manually.
- **Calculate `age` from `dob`** instead of storing both, so they can't disagree.
- **Try a multi-stage build** — not needed at this size, but a good way to make images smaller for bigger apps.
