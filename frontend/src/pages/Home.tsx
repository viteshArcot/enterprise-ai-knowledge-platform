import { useState, useEffect } from 'react';
import type { FC } from 'react';
import { Server, CheckCircle, XCircle, Clock } from 'lucide-react';
import { apiClient } from '../services/api';
import './Home.css';

interface HealthStatus {
  status: string;
  version: string;
  environment: string;
}



export const Home: FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const checkStatus = async () => {
    try {
      const healthData = await apiClient.get<HealthStatus>('/api/v1/health');
      setHealth(healthData);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Health check failed', err);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000); // 30s polling
    return () => clearInterval(interval);
  }, []);

  const StatusIcon = ({ status }: { status?: string }) => {
    if (!status) return <Clock className="text-muted spin" size={24} />;
    return status === 'healthy' ? (
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
            <div className="detail-row">
              <span>Status</span>
              <span className="font-medium capitalize">{health?.status || '...'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
