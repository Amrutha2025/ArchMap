# ArchMap

AI-Powered Code Intelligence Platform

Badges: [License: MIT] [Build: pending]

## Table of Contents
- **About The Project**
- **Getting Started**
- **Architecture**
- **Development**
- **Accessing Services**
- **Environment Variables**
- **Troubleshooting**
- **Contributing**
- **Testing**
- **Deployment**
- **License**
- **Contact**

## About The Project
- **What is ArchMap**: A developer analytics and code intelligence platform that analyzes Git repositories for ownership, coupling, bus-factor, and more.
- **Key features**:
  - Git analysis (ownership, coupling, bus factor)
  - FastAPI backend with async pipeline
  - React/Vite frontend
  - Neo4j (graph), PostgreSQL (relational), Redis (cache)
- **Built with**: FastAPI, React/Vite, Neo4j, PostgreSQL, Redis, SQLAlchemy, GitPython, PyDriller, NetworkX.

## Getting Started
### Prerequisites (Windows/macOS/Linux)
- Docker Desktop (includes Docker Engine and Compose v2)
  - Windows: enable WSL2 backend in Docker Desktop settings
  - Ensure virtualization is enabled in BIOS
- Git
- Optional (Windows corporate networks): proxy exceptions for Docker Hub
  - Docker Desktop → Settings → Resources → Proxies
  - Add to No Proxy: `localhost,127.0.0.1,::1,docker.io,registry-1.docker.io,auth.docker.io,production.cloudflare.docker.com,.cloudflarestorage.com`

### First-time setup
```bash
# 1) Clone and prepare env
git clone https://github.com/username/archmap.git
cd archmap
cp .env.example .env

# 2) Start databases + backend (this will pull images and build backend)
docker compose up -d postgres redis neo4j backend

# 3) Verify backend is healthy
docker compose ps
# Expect: postgres/redis/neo4j = healthy, backend = running/healthy

# 4) Check backend URL
curl http://localhost:8000/health
# or open http://localhost:8000/docs in your browser

# 5) Build the frontend (one-time or when UI changes)
cd frontend
npm install
npm run build
cd ..

# 6) Start the frontend
docker compose up -d frontend

# 7) Follow logs (optional)
docker compose logs -f

# Stop the whole stack later
docker compose down
```

### Windows/PowerShell notes
- Run commands one per line; PowerShell does not support `&&` like Bash.
- Use `Invoke-WebRequest` if `curl` is aliased:
  - `Invoke-WebRequest http://localhost:8000/health -UseBasicParsing | Select-Object StatusCode, Content`

## Architecture
```
                        ┌──────────────┐
                        │   Frontend   │  React/Vite (port 3000)
                        └──────┬───────┘
                               │ HTTP (REST/WebSocket)
                               ▼
                        ┌──────────────┐
                        │   Backend    │  FastAPI (port 8000)
                        └────┬──┬───┬──┘
                             │  │   │
                 Bolt        │  │   │  SQLAlchemy/psycopg2
           ┌─────────────────┘  │   └──────────────────────┐
           ▼                    │                          ▼
     ┌───────────┐         ┌─────────┐               ┌─────────┐
     │   Neo4j   │         │  Redis  │               │PostgreSQL│
     └───────────┘         └─────────┘               └─────────┘
```

### Components
- Neo4j: Graph analytics (APOC + GDS)
- PostgreSQL: Persistent relational storage
- Redis: Caching and job coordination
- Backend: FastAPI app with Git analysis services
- Frontend: React/Vite UI

## Development
### Project Structure
```
backend/
  Dockerfile
  app/
    main.py
    services/
    utils/
    schemas/
    models/
frontend/
  Dockerfile
  index.html
  src/
    main.tsx
    App.tsx
  vite.config.ts
docker-compose.yml
.env.example
```

### Run the whole stack (recommended flow)
```bash
# Start data services + backend
docker compose up -d postgres redis neo4j backend
# Build and start frontend
cd frontend && npm install && npm run build && cd ..
docker compose up -d frontend
```

### Run services individually
- Backend + databases only:
```bash
docker compose up -d postgres redis neo4j backend
```
- Frontend only (after building `frontend/dist`):
```bash
docker compose up -d frontend
```

### Running tests (placeholders)
```bash
# Backend tests
docker compose exec backend pytest -q

# Frontend tests
docker compose exec frontend npm test -- --watchAll=false
```

### Debugging tips
- Ensure .env is present and correct
- Check container health: `docker compose ps`
- View service logs: `docker compose logs -f <service>`
- If Neo4j fails healthcheck, ensure NEO4J_PASSWORD matches .env

## Accessing Services
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **PostgreSQL**: localhost:5432

## Environment Variables
Copy `.env.example` to `.env` and adjust as needed. Key variables:
- Databases: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `POSTGRES_*`, `REDIS_*`
- App: `BACKEND_PORT`, `FRONTEND_PORT`, `ALLOWED_ORIGINS`, `ENVIRONMENT`, `DEBUG`
- Security: `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRATION_DAYS`
- Frontend: `VITE_API_URL`, `VITE_WS_URL`
- Git analysis: `GIT_CACHE_DIR`, `GITHUB_TOKEN`, etc.

Notes:
- `ALLOWED_ORIGINS` already includes `http://localhost:3000`.
- `VITE_API_URL` is passed to the frontend at build-time. To change it, set `frontend/.env` then re-run `npm run build`.

## Troubleshooting
- **Docker pull error: `http: server gave HTTP response to HTTPS client`**
  - Cause: corporate proxy/registry mirror intercepting TLS.
  - Fix: Docker Desktop → Settings → Resources → Proxies. Set correct HTTPS proxy or clear both if not needed. Add to No Proxy:
    `localhost,127.0.0.1,::1,docker.io,registry-1.docker.io,auth.docker.io,production.cloudflare.docker.com,.cloudflarestorage.com`
  - Restart Docker Desktop and retry pulls.
- **Frontend 404 at `/`**
  - Ensure you built the UI: `cd frontend && npm install && npm run build && cd ..`.
  - The compose service serves `./frontend/dist` at port 3000. If `dist` is empty/missing, you’ll see 404 or directory listing.
- **Dev server keeps restarting or `vite` not found**
  - We use a static server for stability. Use `npm run build` and the container will serve prebuilt assets.
- **Ports already in use**
  - Change published ports in `docker-compose.yml` or stop the conflicting service.
- **Neo4j auth issues**
  - `docker compose down -v` to reset volumes, then `docker compose up -d postgres redis neo4j`
- **PowerShell gotchas**
  - Run commands on separate lines; avoid `&&`. Use `;` or one-by-one.

## Contributing
- Open issues and PRs
- Follow conventional commits and code style
- Include tests where possible

## Testing
- Backend: pytest (coming soon)
- Frontend: vitest/jest (coming soon)

## Deployment
- For production, add non-reload servers, secrets management, hardened configs, and CI/CD pipelines

## License
MIT License

## Contact
- Team: team@archmap.local (placeholder)
- Project: https://github.com/username/archmap
