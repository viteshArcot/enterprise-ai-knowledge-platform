# Enterprise AI Knowledge Platform - Production Readiness

This document outlines the architecture, deployment requirements, and configurations necessary to deploy the application securely to production.

## 1. Architecture

The application is designed for a decoupled frontend and backend deployment:

- **Frontend:** Vercel (React + Vite SPA)
- **Backend:** Render (Docker container running FastAPI)
- **Database:** Supabase PostgreSQL with `pgvector` extension
- **Object Storage (Optional Phase):** Currently uses persistent disk on Render (via `UPLOAD_DIRECTORY`), with a planned migration to Cloudflare R2 for scalable object storage.

## 2. Backend Deployment Requirements

- **Platform:** Any container orchestration platform (Render, Railway, Fly.io).
- **Port:** The container exposes port `8000` by default. Platforms that inject a `$PORT` environment variable must map traffic to `8000`, or you can override the Docker command.
- **Disk Persistence:** Because documents are stored locally before being processed (and optionally served for download), the backend requires a persistent disk mounted to the `uploads/` directory if Cloudflare R2 is not yet implemented. On Render, attach a persistent disk to `/app/uploads`.

## 3. Frontend Deployment Requirements

- **Platform:** Vercel, Netlify, or standard Nginx static hosting.
- **Build Command:** `npm run build`
- **Output Directory:** `dist`

## 4. Environment Variables

### Backend Configuration

| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `ENVIRONMENT` | Must be `production` for security. | `production` |
| `DEBUG` | Must be `false`. The app refuses to start in production if `true`. | `false` |
| `SECRET_KEY` | 32+ char random string for cryptographic signing. | (Required) |
| `DATABASE_URL` | Asyncpg connection string to Supabase. | `postgresql+asyncpg://...` |
| `DATABASE_AUTO_CREATE` | Must be `false`. Use Alembic migrations instead. | `false` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins. | `https://your-frontend.vercel.app` |
| `LOG_LEVEL` | Logging verbosity (`INFO`, `WARNING`, `ERROR`). | `INFO` |
| `LOG_FORMAT` | `json` for Datadog/CloudWatch, `console` for local. | `json` |
| `LLM_PROVIDER` | `gemini`, `openrouter`, or `ollama`. | `gemini` |
| `GEMINI_API_KEY` | API key if using Gemini provider. | (Required for Gemini) |

### Frontend Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Public URL of the deployed backend. | `https://api.your-app.onrender.com` |

*(Note: Do not put secrets in `VITE_` variables as they are exposed to the browser.)*

## 5. Alembic Migration Procedure

In production, the database schema must be initialized and updated using Alembic migrations, not SQLAlchemy's `create_all`.

1. Connect to the production database via a secure tunnel or CI/CD pipeline.
2. Run migrations using the Alembic CLI:
   ```bash
   alembic upgrade head
   ```

## 6. Database Initialization

Ensure that the target PostgreSQL database has the `pgvector` extension installed. Supabase supports this out of the box, but it must be enabled via the Supabase dashboard or via an initial migration:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 7. Health Endpoints

- **Liveness:** `GET /api/v1/health` - Fast check (no I/O) to verify the process is alive.
- **Readiness:** `GET /api/v1/health/ready` - Checks external dependencies (e.g., database connectivity).

Use these endpoints for your Render/Vercel health checks.

## 8. CORS Configuration

For security, the backend rejects cross-origin requests by default. Set `CORS_ORIGINS` to the exact URL of your Vercel frontend. Do not use wildcard `*` in production.

## 9. Upload Limits

File uploads are hard-limited by the backend to prevent denial-of-service.
- Maximum size is configurable via `MAX_UPLOAD_SIZE_BYTES` (default: 100MB).
- Uploaded filenames are sanitized and replaced with a UUID on the filesystem to prevent directory traversal attacks.

## 10. Storage Behavior

- Uploaded files are temporarily stored in `UPLOAD_DIRECTORY`.
- If a duplicate file (matching SHA-256 hash) is detected, the backend returns a `409 Conflict`.
- Files are parsed asynchronously.

## 11. Known Free-Tier Limitations

- **Connection Pooling:** Free-tier PostgreSQL databases (like Supabase free tier) often have strict connection limits (e.g., 60-100 connections). Configure `DATABASE_POOL_SIZE` carefully (default is 10) to avoid exhausting connections when scaling the backend.
- **Cold Starts:** Serverless frontends and spin-down backends (Render free tier) will experience 30-50s cold starts if inactive.
- **Disk Storage:** If using a free tier without persistent disk, uploaded files will be lost on container restart.

## 12. Local Development Procedure

Run the local environment using Docker Compose:
```bash
cp .env.example .env
# Fill out required API keys in .env
docker-compose up --build
```
This automatically provisions a local PostgreSQL database, runs the backend, and serves the Vite frontend on port 3000. `DATABASE_AUTO_CREATE=true` is set by default in docker-compose.

## 13. Production Verification Checklist

- [ ] `VITE_API_URL` set correctly in Vercel.
- [ ] `DATABASE_URL` set to production Supabase connection string.
- [ ] `SECRET_KEY` generated and set securely.
- [ ] `CORS_ORIGINS` set to the Vercel production URL.
- [ ] Alembic migrations run successfully against the production DB.
- [ ] `pgvector` extension enabled on the production DB.
- [ ] Persistent disk attached to Render for the `/app/uploads` directory.
- [ ] LLM provider API keys configured on the backend.
