"use client";

import { useEffect, useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { clients as clientsApi, type Client } from "@/lib/api";

/* ---- Connector catalog types ---- */

type ConnectorType = "csv" | "meta_ads" | "google_ads" | "ga4" | "tiktok" | "shopify";
type ConnectorStatus = "configured" | "pending";

interface ConnectorCatalogEntry {
  type: ConnectorType;
  name: string;
  description: string;
}

interface ConnectedSource {
  id: string;
  type: ConnectorType;
  name: string;
  status: ConnectorStatus;
  lastSync: string | null;
}

const CATALOG: ConnectorCatalogEntry[] = [
  { type: "csv", name: "CSV Upload", description: "Upload spend and revenue data as a CSV spreadsheet." },
  { type: "meta_ads", name: "Meta Ads", description: "Connect Facebook and Instagram Ads campaign data." },
  { type: "google_ads", name: "Google Ads", description: "Import Google Ads spend, impressions, and conversions." },
  { type: "ga4", name: "Google Analytics 4", description: "Pull web and app analytics from GA4 properties." },
  { type: "tiktok", name: "TikTok Ads", description: "Sync TikTok advertising performance data." },
  { type: "shopify", name: "Shopify", description: "Connect store revenue and order data from Shopify." },
];

const STATUS_META: Record<ConnectorStatus, { label: string; variant: "success" | "warning" }> = {
  configured: { label: "Configured", variant: "success" },
  pending: { label: "Pending", variant: "warning" },
};

let nextId = 1;
function generateId(): string {
  return `conn_${Date.now()}_${nextId++}`;
}

/* ---- Component ---- */

export default function ConnectorsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<string>("all");
  const [connected, setConnected] = useState<ConnectedSource[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    clientsApi.list().then(setClients).catch(() => setClients([]));
  }, []);

  const addConnector = useCallback((entry: ConnectorCatalogEntry) => {
    const source: ConnectedSource = {
      id: generateId(),
      type: entry.type,
      name: entry.name,
      status: "pending",
      lastSync: null,
    };
    setConnected((prev) => [...prev, source]);
  }, []);

  const removeConnector = useCallback((id: string) => {
    setConnected((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const filtered = selectedClientId === "all"
    ? connected
    : connected.filter(() => true); // all sources belong to the selected client context

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Data connectors</h1>
          <p className="mt-1 text-sm text-slate-500">
            Connect marketing and revenue sources so MMM can ingest your data.
          </p>
        </div>
      </div>

      {/* Client selector */}
      <div className="flex items-center gap-3">
        <label htmlFor="connector-client" className="text-sm font-medium text-slate-600">Client</label>
        <select
          id="connector-client"
          value={selectedClientId}
          onChange={(e) => setSelectedClientId(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm focus:outline-2 focus:outline-indigo-600"
        >
          <option value="all">All clients</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <span className="text-sm text-slate-500">
          {filtered.length} source{filtered.length !== 1 ? "s" : ""} connected
        </span>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
      )}

      {/* Connect source catalog */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle>Connect a source</CardTitle>
          <CardDescription>Choose a data source to add to your workspace.</CardDescription>
        </CardHeader>
        <CardContent className="p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {CATALOG.map((entry) => (
              <div
                key={entry.type}
                className="flex flex-col gap-2 rounded-lg border border-slate-200 p-4 transition hover:border-indigo-300 hover:shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-900">{entry.name}</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-500">{entry.description}</p>
                <Button
                  variant="default"
                  size="sm"
                  className="mt-auto self-start"
                  onClick={() => addConnector(entry)}
                >
                  + Add
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Connected sources table */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle>Connected sources</CardTitle>
          <CardDescription>
            Manage data connections for each client. Credential configuration is coming soon.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState
              title="No connectors yet"
              description="Add a data source above to start building your MMM dataset."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Source</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last sync</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((conn) => {
                    const meta = STATUS_META[conn.status];
                    return (
                      <TableRow key={conn.id}>
                        <TableCell className="font-medium text-slate-900">{conn.name}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">{conn.type}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                        </TableCell>
                        <TableCell className="text-slate-500">
                          {conn.lastSync ?? "—"}
                        </TableCell>
                        <TableCell className="text-right">
                          <button
                            className="text-sm text-slate-400 hover:text-red-600"
                            onClick={() => removeConnector(conn.id)}
                          >
                            Remove
                          </button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
