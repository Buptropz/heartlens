export interface RadarScore {
  score: number;
  label: string;
}

export interface RadarData {
  sincerity: RadarScore;
  engagement: RadarScore;
  respect: RadarScore;
  manipulation: RadarScore;
  communication: RadarScore;
  red_flags: RadarScore;
}

export interface EvidenceItem {
  quote: string;
  analysis: string;
}

export interface DimensionCard {
  dimension: string;
  title: string;
  summary: string;
  evidence: EvidenceItem[];
  suggestion: string;
}

export interface AnalyzeResponse {
  report_id: string;
  share_url: string;
  created_at: string;
  expires_at: string;
  radar: RadarData;
  cards: DimensionCard[];
  overall: string;
}

export interface ApiError {
  error: string;
  detail: string;
}
