/**
 * StatusCard — reusable component to display a dependency's health status.
 *
 * Accepts a status string and renders a colored badge with optional detail.
 * Used in the readiness view to show per-dependency health at a glance.
 */

import type { FC } from 'react';

interface StatusCardProps {
  label: string;
  status: 'healthy' | 'unhealthy' | 'degraded' | 'loading';
  detail?: string;
  value?: string;
}

const STATUS_CONFIG: Record<
  StatusCardProps['status'],
  { color: string; dot: string; label: string }
> = {
  healthy: { color: '#10b981', dot: '●', label: 'Healthy' },
  degraded: { color: '#f59e0b', dot: '●', label: 'Degraded' },
  unhealthy: { color: '#ef4444', dot: '●', label: 'Unhealthy' },
  loading: { color: '#6366f1', dot: '○', label: 'Checking…' },
};

export const StatusCard: FC<StatusCardProps> = ({ label, status, detail, value }) => {
  const config = STATUS_CONFIG[status];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        background: 'rgba(255,255,255,0.04)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        marginBottom: '8px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{ color: config.color, fontSize: '12px' }}>{config.dot}</span>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 500, color: '#e2e8f0' }}>{label}</div>
          {detail && (
            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>{detail}</div>
          )}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <span
          style={{
            fontSize: '12px',
            fontWeight: 600,
            color: config.color,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {value ?? config.label}
        </span>
      </div>
    </div>
  );
};
