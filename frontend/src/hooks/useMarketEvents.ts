import { useState, useEffect, useRef } from 'react';
import type { FundingEvent, TechnologyType } from '../types';

function formatAmount(usd: number | null): string {
  if (!usd || usd <= 0) return '';
  if (usd >= 1_000_000_000) return `$${(usd / 1_000_000_000).toFixed(1)}B`;
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(0)}M`;
  if (usd >= 1_000) return `$${(usd / 1_000).toFixed(0)}K`;
  return `$${usd.toFixed(0)}`;
}

function mapEvent(raw: Record<string, unknown>, idx: number): FundingEvent {
  const amountUsd = (raw.amount_usd as number) ?? null;
  const techIds: string[] = parseJsonArray(raw.technology_ids);
  const techId = (techIds[0] as TechnologyType | undefined) ?? 'embodied-ai';
  const round = (raw.round_stage as string) || (raw.event_type as string) || 'funding';
  const company = (raw.company_name as string) || '';

  return {
    id: (raw.id as string) || `market-${idx}`,
    company: company || 'Unknown',
    round: round.charAt(0).toUpperCase() + round.slice(1),
    amount: formatAmount(amountUsd),
    date: (raw.date as string)?.slice(0, 7) ?? '',
    track: round,
    techId,
  };
}

function parseJsonArray(val: unknown): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val as string[];
  if (typeof val === 'string') {
    try { return JSON.parse(val) as string[]; } catch { return []; }
  }
  return [];
}

export function useMarketEvents(techId: TechnologyType) {
  const [events, setEvents] = useState<FundingEvent[]>([]);
  const [allEvents, setAllEvents] = useState<FundingEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);

    // Fetch ALL events (no tech filter) to populate the scroll feed
    // Also fetch tech-filtered set for the filtered view
    Promise.all([
      fetch(`/api/market-events?limit=100`, { signal: controller.signal }),
      fetch(`/api/market-events?technology_id=${encodeURIComponent(techId)}&limit=100`, { signal: controller.signal }),
    ])
      .then(async ([allRes, filteredRes]) => {
        const allData = allRes.ok ? await allRes.json() : { events: [] };
        const filteredData = filteredRes.ok ? await filteredRes.json() : { events: [] };
        setAllEvents((allData.events || []).map((e: Record<string, unknown>, i: number) => mapEvent(e, i)));
        setEvents((filteredData.events || []).map((e: Record<string, unknown>, i: number) => mapEvent(e, i)));
      })
      .catch(err => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Failed to fetch market events');
        setEvents([]);
        setAllEvents([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [techId]);

  return { events, allEvents, loading, error };
}
