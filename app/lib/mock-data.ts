export interface Client {
  id: string;
  name: string;
  industry: string;
  domain: string;
  currency: string;
  status: 'healthy' | 'needs-data' | 'retrain-due';
}

export const CLIENTS: Client[] = [
  { id: 'acme', name: 'Acme DTC', industry: 'Ecommerce / DTC', domain: 'acme-dtc.com', currency: 'USD', status: 'healthy' },
  { id: 'bloom', name: 'Bloom Retail', industry: 'Retail', domain: 'bloomretail.io', currency: 'USD', status: 'retrain-due' },
  { id: 'core', name: 'Core Electronics', industry: 'Electronics', domain: 'core-electronics.com', currency: 'USD', status: 'needs-data' },
  { id: 'nimbus', name: 'Nimbus Apparel', industry: 'Apparel', domain: 'nimbus.app', currency: 'EUR', status: 'healthy' },
];

export function getClient(id: string): Client | undefined {
  return CLIENTS.find((c) => c.id === id);
}

export type ConnectorStatus = 'connected' | 'syncing' | 'error' | 'not-configured';

export interface Connector {
  id: string;
  clientId: string;
  name: string;
  type: 'API' | 'CSV';
  status: ConnectorStatus;
  account: string;
  lastSync: string | null;
  nextSync: string;
  rowsFetched: number;
}

export const CONNECTORS: Connector[] = [
  { id: 'c1', clientId: 'acme', name: 'Meta Marketing API', type: 'API', status: 'connected', account: 'acme.ads@agency.com', lastSync: '2026-07-31T09:00:00Z', nextSync: 'Sun 2:00 AM', rowsFetched: 42180 },
  { id: 'c2', clientId: 'acme', name: 'Shopify', type: 'API', status: 'connected', account: 'acme-dtc.myshopify.com', lastSync: '2026-07-31T10:00:00Z', nextSync: 'Sun 2:00 AM', rowsFetched: 18304 },
  { id: 'c3', clientId: 'acme', name: 'Google Ads', type: 'API', status: 'error', account: 'acme.dtc@gmail.com', lastSync: '2026-07-24T00:00:00Z', nextSync: 'Sun 2:00 AM', rowsFetched: 9902 },
  { id: 'c4', clientId: 'bloom', name: 'CSV Upload', type: 'CSV', status: 'connected', account: 'spend_revenue_2026.csv', lastSync: '2026-07-15T00:00:00Z', nextSync: '—', rowsFetched: 5200 },
  { id: 'c5', clientId: 'core', name: 'GA4', type: 'API', status: 'not-configured', account: '—', lastSync: null, nextSync: '—', rowsFetched: 0 },
];

export function clientConnectors(clientId: string): Connector[] {
  return CONNECTORS.filter((c) => c.clientId === clientId);
}

export type ModelStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface ChannelResult {
  name: string;
  contribution: number;
  roas: number;
  spend: number;
}

export interface ModelJob {
  id: string;
  clientId: string;
  name: string;
  version: string;
  status: ModelStatus;
  trainedAt: string;
  dateRange: string;
  r2: number | null;
  mape: number | null;
  rhat: number | null;
  duration: string;
  channels: ChannelResult[];
}

export const MODELS: ModelJob[] = [
  {
    id: 'm-100',
    clientId: 'acme',
    name: 'First model — Acme',
    version: 'v1',
    status: 'running',
    trainedAt: '2026-08-01T08:00:00Z',
    dateRange: 'Mar 1 – Jul 31, 2026',
    r2: null,
    mape: null,
    rhat: null,
    duration: '—',
    channels: [],
  },
  {
    id: 'm-101',
    clientId: 'acme',
    name: 'Model — Acme',
    version: 'v2',
    status: 'completed',
    trainedAt: '2026-07-12T09:15:00Z',
    dateRange: 'Jan 1 – Jun 30, 2026',
    r2: 0.79,
    mape: 15.1,
    rhat: 1.02,
    duration: '2m 58s',
    channels: [
      { name: 'meta', contribution: 36, roas: 3.1, spend: 168000 },
      { name: 'google_ads', contribution: 21, roas: 2.5, spend: 91000 },
      { name: 'tiktok', contribution: 14, roas: 1.9, spend: 54000 },
      { name: 'organic', contribution: 19, roas: 5.8, spend: 11000 },
      { name: 'tv', contribution: 10, roas: 1.5, spend: 38000 },
    ],
  },
  {
    id: 'm-102',
    clientId: 'acme',
    name: 'First model — Acme',
    version: 'v3',
    status: 'completed',
    trainedAt: '2026-07-30T14:32:00Z',
    dateRange: 'Mar 1 – Jun 30, 2026',
    r2: 0.84,
    mape: 12.4,
    rhat: 1.01,
    duration: '3m 12s',
    channels: [
      { name: 'meta', contribution: 34, roas: 3.4, spend: 182000 },
      { name: 'google_ads', contribution: 22, roas: 2.8, spend: 98000 },
      { name: 'tiktok', contribution: 16, roas: 2.1, spend: 61000 },
      { name: 'organic', contribution: 18, roas: 6.2, spend: 12000 },
      { name: 'tv', contribution: 10, roas: 1.6, spend: 41000 },
    ],
  },
  {
    id: 'm-104',
    clientId: 'bloom',
    name: 'Model — Bloom',
    version: 'v2',
    status: 'completed',
    trainedAt: '2026-07-15T12:00:00Z',
    dateRange: 'Feb 1 – Jun 30, 2026',
    r2: 0.71,
    mape: 18.2,
    rhat: 1.03,
    duration: '4m 05s',
    channels: [
      { name: 'meta', contribution: 28, roas: 2.9, spend: 120000 },
      { name: 'google_ads', contribution: 24, roas: 2.6, spend: 88000 },
      { name: 'shopify_revenue', contribution: 30, roas: 5.1, spend: 9000 },
      { name: 'radio', contribution: 18, roas: 1.8, spend: 46000 },
    ],
  },
  {
    id: 'm-105',
    clientId: 'core',
    name: 'First model — Core',
    version: 'v1',
    status: 'failed',
    trainedAt: '2026-07-20T16:00:00Z',
    dateRange: 'May 1 – Jun 30, 2026',
    r2: null,
    mape: null,
    rhat: null,
    duration: '—',
    channels: [],
  },
];

export function latestModel(clientId: string): ModelJob | undefined {
  return MODELS.filter((m) => m.clientId === clientId && m.status === 'completed')
    .sort((a, b) => b.trainedAt.localeCompare(a.trainedAt))[0];
}

export function recentModels(clientId: string, limit = 5): ModelJob[] {
  return MODELS.filter((m) => m.clientId === clientId)
    .sort((a, b) => b.trainedAt.localeCompare(a.trainedAt))
    .slice(0, limit);
}

export interface Member {
  id: string;
  name: string;
  email: string;
  role: 'Owner' | 'Analyst' | 'Viewer';
  status: 'Active' | 'Pending';
}

export const MEMBERS: Member[] = [
  { id: 'u1', name: 'Ari Patel', email: 'ari@acmeagency.io', role: 'Owner', status: 'Active' },
  { id: 'u2', name: 'Sam Torres', email: 'sam@acmeagency.io', role: 'Analyst', status: 'Active' },
  { id: 'u3', name: 'Jin Lee', email: 'jin@acmeagency.io', role: 'Analyst', status: 'Active' },
  { id: 'u4', name: 'Casey Chen', email: 'casey@acmeagency.io', role: 'Viewer', status: 'Pending' },
];
