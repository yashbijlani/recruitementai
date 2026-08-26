export type Candidate = {
  id: string;
  name: string;
  current_position?: string;
  current_company?: string;
  industry?: string;
  city?: string;
  experience_years?: number;
  expected_salary?: number;
  notice_period_days?: number;
  email?: string;
  phone?: string;
  education: string[];
  skills: string[];
  suitability_score?: number;
  score_reasons: string[];
  score_gaps: string[];
};

export type Metrics = {
  total_candidates: number;
  screened_candidates: number;
  industries: Record<string, number>;
  positions: Record<string, number>;
  locations: Record<string, number>;
  screening_statuses: Record<string, number>;
  experience_distribution: Record<string, number>;
  salary_distribution: Record<string, number>;
  recent_candidates: Candidate[];
};

export type CandidateFilters = {
  q?: string;
  city?: string;
  position?: string;
  industry?: string;
  min_experience?: string;
  max_salary?: string;
  max_notice_period?: string;
  screening?: string;
  page?: number;
  page_size?: number;
};

const API = process.env.NODE_ENV === "production" ? "/api" : process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = init?.body instanceof FormData ? { ...init?.headers } : { "Content-Type": "application/json", ...init?.headers };
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function getMetrics() { return request<Metrics>("/api/dashboard/metrics"); }
export function getCandidates(filters: CandidateFilters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)); });
  return request<{ items: Candidate[]; total: number; page: number; page_size: number }>(`/api/candidates?${params}`);
}
export function getCandidate(id: string) { return request<Candidate>(`/api/candidates/${id}`); }
export type Recommendation = { rank: number; candidate_id: string; candidate: Candidate; overall_score: number; score_breakdown: Record<string, number>; matched_criteria: string[]; concerns: string[]; explanation: string };
export function getRecommendations(query: string, limit = 10) { return request<{ query: string; parsed_requirements: Record<string, unknown>; results: Recommendation[] }>("/api/recommendations", { method: "POST", body: JSON.stringify({ query, limit }) }); }
export function getStaticRecommendations(limit = 10) { return request<{ query: string; parsed_requirements: Record<string, unknown>; results: Recommendation[] }>(`/api/recommendations/static?limit=${limit}`); }
export function uploadCv(file: File) { const body = new FormData(); body.append("file", file); return request<{ upload_id: string; status: string }>("/api/candidates/upload-cv", { method: "POST", headers: {}, body }); }
export function getUploadStatus(id: string) { return request<{ upload_id: string; status: string; extraction_method?: string; extraction_quality?: number; error?: string }>(`/api/cv-uploads/${id}`); }
export function getUploadProposal(id: string) { return request<{ id: string; changes: { field: string; old_value?: string; new_value?: string }[] }>(`/api/cv-uploads/${id}/proposal`); }
export function approveUpload(id: string) { return request<{ status: string }>(`/api/cv-uploads/${id}/proposal/approve`, { method: "POST" }); }
export function rejectUpload(id: string) { return request<{ status: string }>(`/api/cv-uploads/${id}/proposal/reject`, { method: "POST" }); }
