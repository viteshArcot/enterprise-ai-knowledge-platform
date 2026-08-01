import type { FC } from 'react';
import { Home } from './pages';
import './App.css';

/**
 * App — root application component.
 *
 * Phase 1: Single-page layout with health status dashboard.
 * Phase 4: Will be replaced with a router (React Router v7) wrapping
 *          authenticated and public route trees.
 */
const App: FC = () => {
  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="logo">
            <span className="logo-icon">⬡</span>
            <span className="logo-text">AI Knowledge Platform</span>
          </div>
          <nav className="topbar-nav">
            <a
              href="http://localhost:8000/api/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="nav-link"
            >
              API Docs ↗
            </a>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="nav-link"
            >
              GitHub ↗
            </a>
          </nav>
        </div>
      </header>

      <main className="main">
        <Home />
      </main>

      <footer className="footer">
        <p>
          Enterprise AI Knowledge Platform · Phase 1 ·{' '}
          <a href="https://github.com" target="_blank" rel="noopener noreferrer">
            View on GitHub
          </a>
        </p>
      </footer>
    </div>
  );
};

export default App;
