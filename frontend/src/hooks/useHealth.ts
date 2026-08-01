/**
 * useHealth — React hook for the backend health status.
 *
 * Encapsulates the data-fetching logic for the /api/v1/health endpoint.
 * Components that need health status import this hook — they never call
 * the API client directly.
 *
 * Why custom hooks?
 *   - Reusable data-fetching logic across components
 *   - Single place to add caching, polling, or error retry
 *   - Keeps components focused on rendering, not data management
 *
 * Phase 2: Replace with React Query (TanStack Query) for caching,
 *   background refetching, and stale-while-revalidate behavior.
 */

import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export interface HealthStatus {
  status: string;
  environment: string;
  version: string;
  uptime_seconds: number;
}

export interface UseHealthResult {
  data: HealthStatus | null;
  error: string | null;
  loading: boolean;
  refetch: () => void;
}

export function useHealth(): UseHealthResult {
  const [data, setData] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.get<HealthStatus>('/api/v1/health');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reach the backend API.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchHealth();
  }, [fetchHealth]);

  return { data, error, loading, refetch: fetchHealth };
}
