/** Thin API client for MMM Platform backend (FastAPI). */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

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
  remove: (id: string) =>
    request<void>(`/clients/${id}`, { method: "DELETE" }),
};

/* ---- Models ---- */
export interface ModelConfig {
  name: string;
  draws: number;
  tune: number;
  chains: number;
  adstock_max_lag: number;
  granularity?: string;
}

export interface MediaRecord {
  date: string;
  channel: string;
  spend: number;
  impressions: number;
  clicks: number;
  conversions: number;
  revenue: number;
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

export interface Insight {
  type: string;
  title: string;
  body: string;
  confidence: number;
  metrics: Record<string, number>;
}

export const models = {
  train: (config: ModelConfig, records: MediaRecord[]) =>
    request<FitResult>("/models/train", {
      method: "POST",
      body: JSON.stringify({ config, records }),
    }),
  allocate: (modelId: string, totalBudget: number, channelBounds?: Record<string, [number, number]>) =>
    request<AllocationResult>(`/models/${modelId}/allocate`, {
      method: "POST",
      body: JSON.stringify({ total_budget: totalBudget, channel_bounds: channelBounds }),
    }),
  contributions: (modelId: string) =>
    request<ChannelContribution[]>(`/models/${modelId}/contributions`),
  insights: (modelId: string, clientName?: string) =>
    request<Insight[]>(`/models/${modelId}/insights`, {
      method: "POST",
      body: JSON.stringify({ client_name: clientName ?? "Client" }),
    }),
};
