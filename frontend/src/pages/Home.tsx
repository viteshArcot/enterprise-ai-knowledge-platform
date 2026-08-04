import { useState, useEffect } from 'react';
import type { FC } from 'react';
import { Server, Database, CheckCircle, XCircle, Clock } from 'lucide-react';
import { apiClient } from '../services/api';
import './Home.css';

interface HealthStatus {
  status: string;
  version: string;
  environment: string;
}

interface ReadinessStatus {
  status: string;
  database: string;
  redis: string;
}

export const Home: FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [readiness, setReadiness] = useState<ReadinessStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const checkStatus = async () => {
    try {
      const [healthData, readinessData] = await Promise.all([
        apiClient.get<HealthStatus>('/api/v1/health/'),
        apiClient.get<ReadinessStatus>('/api/v1/health/ready')
      ]);
      setHealth(healthData);
      setReadiness(readinessData);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Health check failed', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000); // 30s polling
    return () => clearInterval(interval);
  }, []);

  const StatusIcon = ({ status }: { status?: string }) => {
    if (!status) return <Clock className="text-muted spin" size={24} />;
    return status === 'ok' ? (
      <CheckCircle className="text-success" size={24} />
    ) : (
      <XCircle className="text-error" size={24} />
    );
  };

  return (
    <div className="status-page animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">System Status</h1>
          <p className="page-subtitle">Real-time health of the Enterprise AI platform components.</p>
        </div>
        <div className="last-updated">
          <Clock size={16} />
          <span>Last updated: {lastUpdated.toLocaleTimeString()}</span>
        </div>
      </div>

      <div className="status-grid">
        <div className="status-card card">
          <div className="status-card-header">
            <div className="status-card-icon bg-primary-light">
              <Server className="text-primary" size={24} />
            </div>
            <StatusIcon status={health?.status} />
          </div>
          <h3>API Gateway</h3>
          <p className="text-muted">Main FastAPI Backend Service</p>
          <div className="status-details">
            <div className="detail-row">
              <span>Version</span>
              <span className="font-medium">{health?.version || '...'}</span>
            </div>
            <div className="detail-row">
              <span>Environment</span>
              <span className="font-medium capitalize">{health?.environment || '...'}</span>
            </div>
          </div>
        </div>

        <div className="status-card card">
          <div className="status-card-header">
            <div className="status-card-icon bg-success-light">
              <Database className="text-success" size={24} />
            </div>
            <StatusIcon status={readiness?.database} />
          </div>
          <h3>Vector Database</h3>
          <p className="text-muted">PostgreSQL with pgvector</p>
          <div className="status-details">
            <div className="detail-row">
              <span>Connection</span>
              <span className={`font-medium ${readiness?.database === 'ok' ? 'text-success' : 'text-error'}`}>
                {readiness?.database === 'ok' ? 'Connected' : (loading ? 'Checking...' : 'Disconnected')}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
