import { useState, useEffect, useRef } from 'react';
import type { Policy } from '../types';
import { enrichPolicy } from '../lib/enrichPolicy';

export interface SimilarPolicyResult {
  policy: Policy;
  score: number;
}

export function useSimilarPolicies(policyId: string | null) {
  const [similarPolicies, setSimilarPolicies] = useState<SimilarPolicyResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!policyId) {
      setSimilarPolicies([]);
      setError(null);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    fetch(`/api/policies/${encodeURIComponent(policyId)}/similar?top_n=5`, {
      signal: controller.signal,
    })
      .then(res => {
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
      })
      .then(data => {
        const enriched = data.map(
          (item: SimilarPolicyResult, i: number) => ({
            policy: enrichPolicy(item.policy, i),
            score: item.score,
          })
        );
        setSimilarPolicies(enriched);
      })
      .catch(err => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Failed to fetch similar policies');
        setSimilarPolicies([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [policyId]);

  return { similarPolicies, loading, error };
}
