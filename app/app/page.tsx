"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { clients as clientsApi, type Client } from "@/lib/api";

export default function DashboardPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadClients = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setClients(await clientsApi.list());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load clients");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadClients();
  }, [loadClients]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Agency dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">Cross-client overview and recent activity.</p>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Active clients", value: loading ? "—" : String(clients.length), sub: "" },
          { label: "Models trained (30d)", value: "N/A", sub: "No training data yet" },
          { label: "Avg. model R²", value: "N/A", sub: "No model data yet" },
          { label: "Insights (30d)", value: "N/A", sub: "No insights yet" },
        ].map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums tracking-tight text-slate-900">{kpi.value}</p>
            <p className="mt-1 text-xs text-slate-500">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* Client overview */}
      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-400 shadow-sm">
          Loading clients...
        </div>
      ) : clients.length === 0 ? (
        <EmptyState
          title="Welcome! Add your first client to get started."
          description="Clients let you organize data, models, and reports per brand."
          actions={<a href="/clients"><Button>+ Add first client</Button></a>}
        />
      ) : (
        <Card>
          <CardHeader className="flex-row items-center justify-between border-b border-slate-100 pb-3">
            <CardTitle>Clients</CardTitle>
            <a href="/clients"><Button size="sm" variant="secondary">View all</Button></a>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Client</TableHead>
                    <TableHead>Slug</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clients.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell>
                        <a href={`/clients/${c.id}`} className="font-medium text-indigo-600 hover:underline">
                          {c.name}
                        </a>
                      </TableCell>
                      <TableCell className="text-slate-600 font-mono text-sm">{c.slug}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">No model</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-sm text-slate-400">Recent activity feed and alerts will render here.</p>
    </div>
  );
}
