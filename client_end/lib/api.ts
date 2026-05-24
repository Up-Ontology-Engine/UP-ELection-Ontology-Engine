export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

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
  if (!res.ok) {
    const message = await res.text().catch(() => "");
    throw new Error(message || `API POST ${path} → ${res.status}`);
  }
  return res.json();
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const message = await res.text().catch(() => "");
    throw new Error(message || `API PATCH ${path} → ${res.status}`);
  }
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE", cache: "no-store" });
  if (!res.ok) {
    const message = await res.text().catch(() => "");
    throw new Error(message || `API DELETE ${path} → ${res.status}`);
  }
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
  twinSnapshot: (acId: string) => get<TwinSnapshot>(`/ac/${acId}/twin-snapshot`).catch(() => null),
  heatmapCoverage: (acId: string) => get<HeatmapCoverage>(`/ac/${acId}/heatmap-coverage`).catch(() => null),

  // Booth-level
  boothSummary: (boothId: string, days = 7) => get<BoothSummary>(`/booth/${boothId}/summary?days=${days}`),
  boothQuality: (boothId: string) => get<BoothQualityResponse>(`/booth/${boothId}/quality`),
  boothNarratives: (boothId: string) => get<{ booth_id: string; narratives: Narrative[] }>(`/booth/${boothId}/narratives`),
  boothContradictions: (boothId: string) => get<ContradictionsResponse>(`/booth/${boothId}/contradictions`),
  boothPulse: (boothId: string, days = 7) => get<PulseResponse>(`/booth/${boothId}/pulse?days=${days}`),
  boothIssues: (boothId: string) => get<{ booth_id: string; issues: Issue[] }>(`/booth/${boothId}/issues`),
  boothComments: (boothId: string) => get<{ booth_id: string; comments: Comment[] }>(`/booth/${boothId}/comments`),
  boothSegments: (boothId: string) => get<BoothSegmentsResponse>(`/booth/${boothId}/segments`).catch(() => null),
  boothConversion: (boothId: string) => get<ConversionOpportunity>(`/booth/${boothId}/conversion`).catch(() => null),

  // Graph
  subgraph: (entityType: string, entityId: string, excludeTypes: string[] = [], limit = 120) => {
    const base = `/graph/subgraph?entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}&limit=${limit}`;
    const excl = excludeTypes.map((t) => `&exclude_types=${encodeURIComponent(t)}`).join("");
    return get<GraphResult>(base + excl);
  },

  // Reasoning
  reason: (question: string) => post<ReasoningResult>("/reasoning/query", { question }),

  // Voter Conversion Engine
  conversion: {
    overview: (acId: string) => get<{ ac_id: string; booths: ConversionBoothSummary[] }>(`/ac/${acId}/conversion-overview`),
    stats: (acId: string) => get<ConversionStats>(`/ac/${acId}/conversion-stats`),
    targets: (boothId: string, contacted?: boolean, limit = 200) => {
      const ct = contacted === undefined ? "" : `&contacted=${contacted}`;
      return get<{ booth_id: string; count: number; targets: BeneficiaryRow[] }>(`/booth/${boothId}/conversion-targets?limit=${limit}${ct}`);
    },
    contact: (id: string, notes?: string, workerId?: string) =>
      patch<{ beneficiary_id: string; contacted: boolean }>(`/beneficiaries/${id}/contact`, { notes, worker_id: workerId }),
    import: (rows: Partial<BeneficiaryRow>[]) =>
      post<{ imported: number }>("/beneficiaries/import", { rows }),
    seedDemo: (acId: string, perBooth = 18) =>
      post<{ ac_id: string; seeded: number }>(`/ac/${acId}/conversion/seed-demo?per_booth=${perBooth}`, {}),
  },

  // Chat session persistence
  chat: {
    sessions: (limit = 50) => get<{ sessions: ChatSession[] }>(`/chat/sessions?limit=${limit}`),
    createSession: (title?: string) => post<ChatSession>("/chat/sessions", { title }),
    getSession: (id: string) => get<ChatSession>(`/chat/sessions/${id}`),
    messages: (id: string) => get<{ session_id: string; messages: ChatMessage[] }>(`/chat/sessions/${id}/messages`),
    addMessage: (id: string, msg: { role: string; content: string; result?: unknown; ts: string }) =>
      post<ChatMessage>(`/chat/sessions/${id}/messages`, msg),
    renameSession: (id: string, title: string) =>
      patch<{ session_id: string; title: string }>(`/chat/sessions/${id}/title`, { title }),
    deleteSession: (id: string) => del<{ deleted: string }>(`/chat/sessions/${id}`),
  },

  // Infrastructure
  infraOverview: () => get<InfraOverview>("/infrastructure/overview"),
  graphCoverage: (acId: string) => get<GraphCoverageResponse>(`/ac/${acId}/graph-coverage`),

  // Ontology live status
  ontologyStatus: () => get<OntologyStatus>("/ontology/status").catch(() => null),

  // Intelligence summary (PG voter stats + Neo4j issues/videos/candidates)
  intelSummary: (acId: string) => get<AcIntelSummary>(`/ac/${acId}/intel-summary`),

  // Election results (Form-20 ingested)
  electionResults: (acId: string, year = 2022) => get<AcElectionResults>(`/ac/${acId}/election-results?year=${year}`),

  // Per-booth election rows (bulk)
  boothElectionRows: (acId: string, year = 2022) => get<BoothElectionRowsResponse>(`/ac/${acId}/booth-election-rows?year=${year}`),
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
  source_breakdown: SourceBreakdown[];
  narratives: Narrative[];
  contradictions: ContradictionFlag[];
  key_insight: string;
  recommendation: string;
}

export interface SourceBreakdown {
  source_type: string;
  event_count: number;
  avg_pulse: number | null;
  positive: number;
  negative: number;
  neutral: number;
}

export interface QualityMetric {
  metric: string;
  value: number | null;
  label: string;
}

export interface PulseRow {
  entity: string;
  pulse_score: number | null;
  event_count: number;
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

export interface WebResult {
  title: string;
  snippet: string;
  url: string;
  source: string;
}

export interface ReasoningResult {
  question: string;
  cypher: string | null;
  /** Raw records from Neo4j */
  graph_results: Record<string, unknown>[];
  /** Legacy alias for graph_results */
  results: Record<string, unknown>[];
  web_results: WebResult[];
  /** LLM-synthesized comprehensive answer */
  answer: string;
  summary: string | null;
  sources: string[];
  mode: "graph" | "web" | "hybrid" | "llm";
  row_count: number;
  elapsed_ms: number;
  error: string | null;
}

export interface OntologyConstraint {
  name: string;
  type: string;
  labels: string[];
  properties: string[];
}

export interface OntologyStatus {
  neo4j: {
    online: boolean;
    nodes: Record<string, number>;
    relationships: Record<string, number>;
    constraints: OntologyConstraint[];
    total_nodes: number;
    total_edges: number;
  };
  postgresql: {
    online: boolean;
    tables: Record<string, number | null>;
  };
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

export interface HeatmapCoverage {
  ac_id: string;
  total_booths: number;
  geocoded_booths: number;
  coverage_pct: number;
  target_pct: number;
  target_met: boolean;
  booths_needed_for_target: number;
}

export interface TwinSnapshot {
  ac_id: string;
  snapshot_generated_at: string;
  ontology: {
    neo4j_online: boolean;
    postgres_online: boolean;
    total_nodes: number;
    total_edges: number;
    active_constraints: number;
  };
  heatmap: HeatmapCoverage;
  demographics_summary: DemographicsSummary | null;
  demographic_segments: { name: string; booth_count: number; description: string; booth_ids: string[] }[];
}

export interface InfraOverview {
  postgresql: Record<string, number | null>;
  neo4j: {
    nodes_by_type: Record<string, number>;
    edges_by_type: Record<string, number>;
    total_nodes: number;
    total_edges: number;
  };
}

export interface GraphCoverageBooth {
  booth_id: string;
  booth_number: number;
  name: string;
  lat: number | null;
  lon: number | null;
  total_voters: number | null;
  bjp_pulse_score: number | null;
  opp_pulse_score: number | null;
  confidence_label: string | null;
  event_count: number | null;
  in_neo4j: boolean;
  neo4j_degree: number;
}

export interface GraphCoverageResponse {
  ac_id: string;
  total: number;
  in_neo4j: number;
  booths: GraphCoverageBooth[];
}

export interface BoothElectionRow {
  booth_id: string;
  booth_number: number;
  party: string;
  votes: number;
  vote_share: number;
  winner_flag: boolean;
  turnout_percent: number | null;
  registered: number | null;
  cast: number | null;
}

export interface BoothElectionRowsResponse {
  ac_id: string;
  year: number;
  rows: BoothElectionRow[];
}

export interface AcElectionResults {
  ac_id: string;
  year: number;
  results: { party: string; total_votes: number; vote_share_pct: number; booths_won: number }[];
  turnout: { total_voters: number; total_votes: number; turnout_pct: number } | null;
}

export interface VoterSegment {
  segment_type: string;
  count: number;
  pct_of_voters: number | null;
}

export interface BoothSegmentsResponse {
  booth_id: string;
  segments: VoterSegment[];
}

export interface ConversionOpportunity {
  booth_id: string;
  persuasion_room_score: number | null;
  beneficiary_density_score: number | null;
  turnout_mobilization_score: number | null;
  service_risk_score: number | null;
  overall_conversion_score: number | null;
  recommended_action: string | null;
  action_reason: string | null;
  computed_at: string | null;
}

export interface AcIntelSummary {
  ac_id: string;
  voter_stats: {
    total: number;
    total_voters: number;
    male_voters: number;
    female_voters: number;
  };
  issues: { code: string; label: string; count: number }[];
  youtube_count: number;
  videos: { title: string; url: string | null; channel: string | null }[];
  candidates: {
    name: string;
    year: number | null;
    candidate_id: string;
    is_incumbent: boolean | null;
    is_primary_opp: boolean | null;
    party: string | null;
  }[];
}

export type PartyLean = "BJP" | "SP" | "BSP" | "INC" | "OTHERS" | "UNKNOWN";

export interface BeneficiaryRow {
  beneficiary_id: string;
  voter_id: string | null;
  name: string;
  father_name: string | null;
  address: string | null;
  ward: string | null;
  locality: string | null;
  scheme_name: string;
  benefit_desc: string | null;
  phone: string | null;
  party_lean: PartyLean;
  contacted: boolean;
  contact_date: string | null;
  contact_notes: string | null;
  worker_id: string | null;
}

export interface ConversionBoothSummary {
  booth_id: string;
  booth_number: number;
  booth_name: string | null;
  total: number;
  supporters: number;
  targets: number;
  unknown_lean: number;
  opp_lean: number;
  contacted: number;
  targets_contacted: number;
}

export interface ConversionStats {
  ac_id: string;
  total_beneficiaries: number;
  total_supporters: number;
  total_targets: number;
  total_contacted: number;
  targets_contacted: number;
  booths_with_data: number;
  contact_rate_pct: number;
  target_contact_pct: number;
  top_schemes: { scheme: string; count: number }[];
}

export interface ChatSession {
  session_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  result: ReasoningResult | null;
  ts: string;
  created_at: string;
}
