/**
 * Home page — Phase 1 platform dashboard.
 *
 * Displays the API health status to confirm frontend ↔ backend connectivity.
 * This page will become the authenticated dashboard entry point in Phase 4.
 */

import type { FC } from 'react';
import { StatusCard } from '../components';
import { useHealth } from '../hooks';

export const Home: FC = () => {
  const { data, error, loading, refetch } = useHealth();

  const apiStatus = loading
    ? 'loading'
    : error
      ? 'unhealthy'
      : data?.status === 'healthy'
        ? 'healthy'
        : 'degraded';

  return (
    <div className="page">
      {/* Hero */}
      <div className="hero">
        <div className="hero-badge">Phase 1 · Engineering Foundation</div>
        <h1 className="hero-title">
          Enterprise AI
          <br />
          <span className="gradient-text">Knowledge Platform</span>
        </h1>
        <p className="hero-subtitle">
          Production-grade AI knowledge management infrastructure built with FastAPI, React, and
          PostgreSQL.
        </p>
      </div>

      {/* Status panel */}
      <div className="card">
        <div className="card-header">
          <h2>System Status</h2>
          <button
            onClick={refetch}
            className="btn-ghost"
            disabled={loading}
            aria-label="Refresh status"
          >
            {loading ? '↻' : '↺'} Refresh
          </button>
        </div>

        <StatusCard
          label="Backend API"
          status={apiStatus}
          detail={
            data
              ? `v${data.version} · ${data.environment} · up ${data.uptime_seconds}s`
              : (error ?? 'Connecting…')
          }
        />
        <StatusCard label="Frontend" status="healthy" detail="React 19 · TypeScript · Vite 8" />
      </div>

      {/* Tech stack */}
      <div className="card">
        <div className="card-header">
          <h2>Technology Stack</h2>
        </div>
        <div className="stack-grid">
          {[
            { layer: 'API', tech: 'FastAPI + Python 3.12' },
            { layer: 'Database', tech: 'PostgreSQL 16 + SQLAlchemy 2' },
            { layer: 'Frontend', tech: 'React 19 + TypeScript + Vite 8' },
            { layer: 'Config', tech: 'Pydantic Settings v2' },
            { layer: 'Logging', tech: 'Structlog (JSON)' },
            { layer: 'Container', tech: 'Docker + Compose' },
          ].map(({ layer, tech }) => (
            <div key={layer} className="stack-item">
              <span className="stack-layer">{layer}</span>
              <span className="stack-tech">{tech}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Roadmap pills */}
      <div className="card">
        <div className="card-header">
          <h2>Development Roadmap</h2>
        </div>
        <div className="roadmap">
          {[
            { phase: 'Phase 1', label: 'Engineering Foundation', done: true },
            { phase: 'Phase 2', label: 'Document Ingestion + Storage', done: false },
            { phase: 'Phase 3', label: 'RAG Pipeline + Semantic Search', done: false },
            { phase: 'Phase 4', label: 'Authentication + Multi-tenancy', done: false },
          ].map(({ phase, label, done }) => (
            <div key={phase} className={`roadmap-item ${done ? 'done' : ''}`}>
              <span className="roadmap-phase">{phase}</span>
              <span className="roadmap-label">{label}</span>
              {done && <span className="roadmap-badge">✓ Complete</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
