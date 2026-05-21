const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API POST ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  health: () => get<{ status: string; ac: string }>("/health"),

  // AC-level
  booths: (acId: string) => get<BoothsResponse>(`/ac/${acId}/booths`),
  candidates: (acId: string) => get<{ ac_id: string; candidates: Candidate[] }>(`/ac/${acId}/candidates`),
  schemes: (acId: string) => get<{ ac_id: string; schemes: SchemeGap[] }>(`/ac/${acId}/schemes`),
  narratives: (acId: string) => get<{ ac_id: string; narratives: Narrative[] }>(`/ac/${acId}/narratives`),
  events: (acId: string, limit = 50) => get<{ ac_id: string; events: PoliticalEvent[] }>(`/ac/${acId}/events?limit=${limit}`),
  quality: (acId: string) => get<AcQuality>(`/ac/${acId}/quality`),
  recommendations: (acId: string) => get<AcRecommendations>(`/ac/${acId}/recommendations`),
  geo: (acId: string) => get<GeoResponse>(`/ac/${acId}/geo`),
  demographics: (acId: string) => get<DemographicsSummary>(`/ac/${acId}/demographics/summary`).catch(() => null),
  demographicSegments: (acId: string) => get<DemographicSegments>(`/ac/${acId}/demographics/segments`).catch(() => null),

  // Booth-level
  boothSummary: (boothId: string, days = 7) => get<BoothSummary>(`/booth/${boothId}/summary?days=${days}`),
  boothQuality: (boothId: string) => get<BoothQualityResponse>(`/booth/${boothId}/quality`),
  boothNarratives: (boothId: string) => get<{ booth_id: string; narratives: Narrative[] }>(`/booth/${boothId}/narratives`),
  boothContradictions: (boothId: string) => get<ContradictionsResponse>(`/booth/${boothId}/contradictions`),
  boothPulse: (boothId: string, days = 7) => get<PulseResponse>(`/booth/${boothId}/pulse?days=${days}`),
  boothIssues: (boothId: string) => get<{ booth_id: string; issues: Issue[] }>(`/booth/${boothId}/issues`),
  boothComments: (boothId: string) => get<{ booth_id: string; comments: Comment[] }>(`/booth/${boothId}/comments`),

  // Graph
  subgraph: (entityType: string, entityId: string) =>
    get<GraphResult>(`/graph/subgraph?entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}`),

  // Reasoning
  reason: (question: string) => post<ReasoningResult>("/reasoning/query", { question }),
};

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BoothRow {
  booth_id: string;
  booth_number: number;
  name: string;
  locality_hint: string | null;
  total_voters: number | null;
  male_voters: number | null;
  female_voters: number | null;
  bjp_pulse_score: number | null;
  opp_pulse_score: number | null;
  digital_lean: number | null;
  digital_lean_label: string | null;
  top_issue: string | null;
  confidence_label: string | null;
  event_count: number | null;
}

export interface BoothsResponse {
  ac_id: string;
  count: number;
  booths: BoothRow[];
}

export interface HistoricalResult {
  election_year: number;
  party: string;
  votes: number | null;
  vote_share: number | null;
  winner_flag: boolean;
}

export interface Issue {
  issue: string;
  mention_count: number;
  avg_polarity: number | null;
  negative_count: number;
  positive_count: number;
}

export interface Comment {
  content: string;
  source: string;
  created_at: string;
  final_issue: string | null;
  final_polarity: number | null;
}

export interface SchemeGap {
  scheme_name: string;
  gap_type: string;
  priority: string;
  severity_score: number | null;
  booth_id?: string;
}

export interface Narrative {
  narrative_type: string;
  strength: number | null;
  summary: string | null;
  booth_id?: string;
}

export interface PoliticalEvent {
  event_id?: string;
  event_type: string;
  event_date: string;
  description: string | null;
  entity: string | null;
  booth_id?: string;
}

export interface Candidate {
  candidate_id: string;
  name: string;
  party: string;
  election_year: number;
  votes: number | null;
  vote_share: number | null;
  winner_flag: boolean;
}

export interface GeoRow {
  booth_id: string;
  booth_number: number;
  name: string;
  locality_hint: string | null;
  total_voters: number | null;
  lat: number;
  lon: number;
  bjp_pulse_score: number | null;
  opp_pulse_score: number | null;
  digital_lean: number | null;
  digital_lean_label: string | null;
  top_issue: string | null;
  confidence_label: string | null;
}

export interface GeoResponse {
  ac_id: string;
  count: number;
  geo: GeoRow[];
}

export interface BoothSummary {
  booth_id: string;
  booth_number: number | null;
  name: string | null;
  ac_name: string;
  total_voters: number | null;
  male_voters: number | null;
  female_voters: number | null;
  historical: {
    bjp_won_count: number;
    bjp_vote_shares: number[];
    trend: string;
    full_history: HistoricalResult[];
  };
  digital_pulse: {
    lean_label: string;
    bjp_pulse: number | null;
    opp_pulse: number | null;
    digital_lean: number | null;
    pulse_detail: PulseRow[];
  };
  confidence: {
    label: string;
    score: number | null;
    event_count: number;
  };
  data_quality: QualityMetric[];
  top_issues: Issue[];
  issue_momentum: Record<string, number>;
  backing_comments: Comment[];
  scheme_analysis: SchemeGap[];
  narratives: Narrative[];
  contradictions: ContradictionFlag[];
  key_insight: string;
  recommendation: string;
}

export interface QualityMetric {
  metric: string;
  value: number | null;
  label: string;
}

export interface PulseRow {
  source: string;
  event_count: number;
  avg_polarity: number | null;
  bjp_events: number;
  opp_events: number;
}

export interface ContradictionFlag {
  entity: string;
  source_a: string;
  source_b: string;
  flag_label: string;
  delta: number | null;
  booth_id?: string;
}

export interface BoothQualityResponse {
  booth_id: string;
  quality: QualityMetric[];
}

export interface ContradictionsResponse {
  booth_id: string;
  has_mixed_signals: boolean;
  contradictions: ContradictionFlag[];
}

export interface PulseResponse {
  booth_id: string;
  window_days: number;
  pulse: PulseRow[];
}

export interface AcQuality {
  ac_id: string;
  total_booths: number;
  booths_with_pulse: number;
  avg_confidence: number | null;
  quality_distribution: Record<string, number>;
}

export interface AcRecommendations {
  ac_id: string;
  risks: string[];
  opportunities: string[];
  actions: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface GraphResult {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ReasoningResult {
  question: string;
  cypher: string;
  results: Record<string, unknown>[];
  summary: string;
}

export interface DemographicsSummary {
  ac_id: string;
  total_voters: number;
  male_voters: number;
  female_voters: number;
  gender_ratio: number;
  booths_with_data: number;
}

export interface DemographicSegments {
  ac_id: string;
  segments: {
    name: string;
    booth_count: number;
    description: string;
    booth_ids: string[];
  }[];
}
