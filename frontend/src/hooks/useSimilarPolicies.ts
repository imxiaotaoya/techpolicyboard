import { useState, useEffect, useRef } from 'react';
import type { Policy } from '../types';
import { COUNTRY_ISO3, COUNTRY_COORDS, deriveInnovationStage } from '../constants';

export interface SimilarPolicyResult {
  policy: Policy;
  score: number;
}

function enrichSimilar(p: Policy, idx: number): Policy {
  const dept = p.department as string;
  if (!p.departmentLabel || p.departmentLabel === 'Unknown') {
    p.departmentLabel = dept === 'Unknown' ? '国际' : (dept || '国际');
  }
  if (!p.iso3) p.iso3 = COUNTRY_ISO3[p.country] ?? 'OTH';
  if (!p.coordinates) {
    const base = COUNTRY_COORDS[p.country] ?? { x: 50, y: 50 };
    const jitter = (idx % 5) - 2;
    p.coordinates = { x: base.x + jitter * 3, y: base.y + ((idx >> 1) % 5 - 2) * 3 };
  }
  if (!p.innovationStage) p.innovationStage = deriveInnovationStage(p);
  if (!p.keywords) {
    const kws = new Set<string>();
    p.relatedTechnologies.slice(0, 3).forEach(t => kws.add(t));
    p.relatedIndustries.slice(0, 2).forEach(t => kws.add(t));
    p.keywords = Array.from(kws);
  }
  if (!p.highlights) {
    p.highlights = [p.summary.slice(0, 40), p.departmentLabel + ' · ' + p.date];
  }
  return p;
}

export function useSimilarPolicies(policyId: string | null) {
  const [similarPolicies, setSimilarPolicies] = useState<SimilarPolicyResult[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!policyId) {
      setSimilarPolicies([]);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);

    fetch(`/api/policies/${encodeURIComponent(policyId)}/similar?top_n=5`, {
      signal: controller.signal,
    })
      .then(res => {
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
      })
      .then(data => {
        const enriched = data.map((item: SimilarPolicyResult, i: number) => ({
          policy: enrichSimilar(item.policy, i),
          score: item.score,
        }));
        setSimilarPolicies(enriched);
      })
      .catch(err => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setSimilarPolicies([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [policyId]);

  return { similarPolicies, loading };
}
