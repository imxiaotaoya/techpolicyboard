import { useState, useEffect, useCallback, useRef } from 'react';
import type { Policy } from '../types';
import { enrichPolicy } from '../lib/enrichPolicy';

export interface PolicyFilters {
  department?: string;
  country?: string;
  level?: string;
  innovationStage?: string;
  techId?: string;
  industryId?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: string;
}

export function usePolicies(filters: PolicyFilters = {}) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchPolicies = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (filters.department) params.set('department', filters.department);
      if (filters.country) params.set('country', filters.country);
      if (filters.level) params.set('level', filters.level);
      if (filters.innovationStage) params.set('innovation_stage', filters.innovationStage);
      if (filters.techId) params.set('tech_id', filters.techId);
      if (filters.industryId) params.set('industry_id', filters.industryId);
      if (filters.dateFrom) params.set('date_from', filters.dateFrom);
      if (filters.dateTo) params.set('date_to', filters.dateTo);
      params.set('page', String(filters.page ?? 1));
      params.set('page_size', String(filters.pageSize ?? 200));
      if (filters.sortBy) params.set('sort_by', filters.sortBy);
      if (filters.sortOrder) params.set('sort_order', filters.sortOrder);

      const res = await fetch(`/api/policies?${params.toString()}`, {
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const data = await res.json();
      const enriched = data.policies.map((p: Policy, i: number) => enrichPolicy(p, i));
      setPolicies(enriched);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      setError(err instanceof Error ? err.message : 'Failed to fetch policies');
      setPolicies([]);
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, [
    filters.department, filters.country, filters.level, filters.innovationStage,
    filters.techId, filters.industryId, filters.dateFrom, filters.dateTo,
    filters.page, filters.pageSize, filters.sortBy, filters.sortOrder,
  ]);

  useEffect(() => {
    fetchPolicies();
    return () => abortRef.current?.abort();
  }, [fetchPolicies]);

  return { policies, total, totalPages, loading, error, refetch: fetchPolicies };
}
