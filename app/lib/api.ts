/** Thin API client for MMM Platform backend (FastAPI). */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "mmm_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      detail = JSON.parse(body)?.detail ?? body;
    } catch {
      /* keep raw body */
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/* ---- Auth ---- */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  org_id: string;
  role: string;
  email?: string | null;
}

export const auth = {
  register: (body: { email: string; password: string; name?: string; organization_name?: string }) =>
    request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => request<AuthResponse>("/auth/me"),
};

/* ---- Clients ---- */
export interface Client {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
}

export const clients = {
  list: () => request<Client[]>("/clients"),
  create: (body: { name: string; slug?: string }) =>
    request<Client>("/clients", { method: "POST", body: JSON.stringify(body) }),
  get: (id: string) => request<Client>(`/clients/${id}`),
  remove: (id: string) => request<void>(`/clients/${id}`, { method: "DELETE" }),
};

/* ---- Models ---- */
export interface ModelConfig {
  name: string;
  draws?: number;
  tune?: number;
  chains?: number;
  adstock_max_lag?: number;
  granularity?: string;
}

export interface MediaRecord {
  date: string;
  channel: string;
  spend: number;
  impressions?: number;
  clicks?: number;
  conversions?: number;
  revenue?: number;
}

export interface FitResult {
  model_name: string;
  model_id: string;
  status: string;
  diagnostics: {
    r2: number;
    mape: number;
    converged: boolean;
    rhat_max: number;
  } | null;
  error: string | null;
}

export interface Allocation {
  channel: string;
  allocated_budget: number;
  share: number;
  expected_revenue: number;
}

export interface AllocationResult {
  total_budget: number;
  allocations: Allocation[];
  expected_total_revenue: number;
}

export interface ChannelContribution {
  channel: string;
  contribution: number;
  share: number;
  roas: number;
  spend: number;
}

export interface ModelJob {
  id: string;
  organization_id: string;
  client_id: string | null;
  name: string;
  status: string;
  error?: string | null;
  r2?: number | null;
  mape?: number | null;
  duration_seconds?: number | null;
  created_at?: string | null;
}

export const models = {
  train: (config: ModelConfig, records: MediaRecord[], client_id?: string) =>
    request<{ model_job_id: string; status: string; channels: string[] }>("/models/train", {
      method: "POST",
      body: JSON.stringify({ config, records, client_id }),
    }),
  trainSync: (config: ModelConfig, records: MediaRecord[], client_id?: string) =>
    request<FitResult>("/models/train-sync", {
      method: "POST",
      body: JSON.stringify({ config, records, client_id }),
    }),
  list: () => request<ModelJob[]>("/models"),
  get: (id: string) => request<ModelJob>(`/models/${id}`),
  allocate: (modelId: string, totalBudget: number, channelBounds?: Record<string, [number, number]>) =>
    request<AllocationResult>(`/models/${modelId}/allocate`, {
      method: "POST",
      body: JSON.stringify({ total_budget: totalBudget, channel_bounds: channelBounds }),
    }),
  contributions: (modelId: string) => request<ChannelContribution[]>(`/models/${modelId}/contributions`),
  insights: (modelId: string, clientName?: string) =>
    request<Insight[]>(`/models/${modelId}/insights`, {
      method: "POST",
      body: JSON.stringify({ client_name: clientName ?? "Client" }),
    }),
};

/* ---- Reports ---- */
export interface ReportGenerateRequest {
  records: MediaRecord[];
  config: ModelConfig;
  client_name: string;
  total_budget: number;
}

export interface Report {
  report_id: string;
  client_name: string;
  markdown: string;
  contributions: ChannelContribution[];
  allocation: AllocationResult;
}

export const reports = {
  generate: (body: ReportGenerateRequest) =>
    request<{ report_id: string; markdown: string }>("/reports/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  list: () => request<{ report_id: string; client_name: string; created_at: string }[]>("/reports"),
  get: (id: string) => request<Report>(`/reports/${id}`),
  pdfUrl: (id: string) => `${API_BASE}/reports/${id}/pdf`,
};

/* ---- Insights ---- */
export interface Insight {
  type: string;
  title: string;
  body: string;
  confidence: number;
  metrics: Record<string, number>;
}
