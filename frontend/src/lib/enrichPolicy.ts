/** Shared policy enrichment — single source of truth for all enrichment sites. */
import type { Policy } from '../types';
import {
  COUNTRY_ISO3,
  COUNTRY_COORDS,
  deriveInnovationStage,
  deriveTechDomain,
} from '../constants';

export function enrichPolicy(p: Policy, idx: number): Policy {
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
  if (!p.techDomain) p.techDomain = deriveTechDomain(p);
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
