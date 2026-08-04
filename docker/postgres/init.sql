-- =============================================================================
-- PostgreSQL initialization script
-- =============================================================================
-- Runs automatically on first container start (via Docker's
-- /docker-entrypoint-initdb.d/ mechanism).
-- This script creates the database structure that Phase 2 will populate
-- with Alembic-managed migrations.
-- =============================================================================

-- Enable UUID generation (used for primary keys)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable vector storage for Phase 2 embeddings.
CREATE EXTENSION IF NOT EXISTS "vector";

-- ---------------------------------------------------------------------------
-- Application role (principle of least privilege)
-- ---------------------------------------------------------------------------
-- In production, the application connects with a restricted role that has
-- only the permissions it needs (no SUPERUSER, no CREATEDB).
-- For local development, we use the postgres superuser for simplicity.
-- ---------------------------------------------------------------------------

-- Placeholder for Phase 2: Alembic will create the actual table schema.
-- This script only sets up extensions and verifies connectivity.

SELECT version() AS postgresql_version;
