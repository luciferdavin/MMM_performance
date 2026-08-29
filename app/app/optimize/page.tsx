"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { clients as clientsApi, models as modelsApi, type Client, type MediaRecord, type AllocationResult } from "@/lib/api";

function sampleRecords(): MediaRecord[] {
  const channels = ["meta", "google_ads", "tiktok", "tv", "radio"] as const;
  const base = { meta: 3000, google_ads: 2500, tiktok: 1500, tv: 1000, radio: 500 };
  const eff = { meta: 3.5, google_ads: 4.0, tiktok: 3.0, tv: 1.5, radio: 1.2 };
  const out: MediaRecord[] = [];
  for (let w = 0; w < 12; w++) {
    const d = new Date(Date.UTC(2026, 0, 5 + 7 * w)).toISOString().slice(0, 10);
    for (const ch of channels) {
      const spend = base[ch] * (1 + 0.1 * Math.sin(w));
      const revenue = spend * eff[ch] * 0.9;
      out.push({
        date: d, channel: ch, spend: +spend.toFixed(2),
        impressions: Math.round(spend * 1500), clicks: Math.round(spend * 30),
        conversions: Math.round(revenue / 80), revenue: +revenue.toFixed(2),
      });
    }
  }
  return out;
}

export default function OptimizePage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [modelId, setModelId] = useState<string | null>(null);
  const [training, setTraining] = useState(false);
  const [budget, setBudget] = useState(50000);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AllocationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    clientsApi.list().then(setClients).catch(() => setClients([]));
  }, []);

  const train = useCallback(async () => {
    setTraining(true);
    setError(null);
    setResult(null);
    try {
      const fit = await modelsApi.trainSync(
        { name: "optimizer-demo", draws: 100, tune: 100, chains: 1, adstock_max_lag: 4 },
        sampleRecords(),
      );
      if (fit.status !== "ok") throw new Error(fit.error ?? "train failed");
      setModelId(fit.model_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Train failed");
    } finally {
      setTraining(false);
    }
  }, []);

  const allocate = useCallback(async () => {
    if (!modelId) return;
    setRunning(true);
    setError(null);
    try {
      setResult(await modelsApi.allocate(modelId, budget));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Allocate failed");
    } finally {
      setRunning(false);
    }
  }, [modelId, budget]);

  const maxAlloc = result ? Math.max(...result.allocations.map((a) => a.allocated_budget), 1) : 1;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Budget optimizer</h1>
        <p className="mt-1 text-sm text-slate-500">Reallocate budget across channels with what-if scenarios.</p>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Constraints</CardTitle>
            <CardDescription>Train a demo model, then set total budget and run.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700">Client</label>
              <select className="mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-2 focus:outline-indigo-600">
                {(clients.length ? clients : [{ id: "demo", name: "Demo client" }]).map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <Button onClick={train} disabled={training} className="w-full">
              {training ? "Training model…" : modelId ? "Retrain demo model" : "Train demo model"}
            </Button>

            <div>
              <label className="block text-sm font-medium text-slate-700">Total weekly budget ($)</label>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(+e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm tabular-nums text-slate-900 shadow-sm focus:outline-2 focus:outline-indigo-600"
              />
            </div>

            <Button onClick={allocate} disabled={!modelId || running} className="w-full">
              {running ? "Optimizing…" : "Run optimization"}
            </Button>
            {modelId && <p className="text-xs text-slate-400">Model: {modelId}</p>}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Results</CardTitle>
            <CardDescription>
              {result
                ? `Recommended allocation for $${result.total_budget.toLocaleString()}`
                : "Set constraints and run to see recommended allocation."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!result && (
              <p className="text-sm text-slate-400">No results yet. Train the demo model, then run optimization.</p>
            )}
            {result && result.allocations.map((a) => (
              <div key={a.channel}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-700">{a.channel}</span>
                  <span className="tabular-nums text-slate-500">
                    ${a.allocated_budget.toLocaleString()} · {Math.round(a.share * 100)}%
                  </span>
                </div>
                <div className="h-2.5 w-full rounded-full bg-slate-100">
                  <div
                    className="h-2.5 rounded-full bg-indigo-600 transition-all"
                    style={{ width: `${(a.allocated_budget / maxAlloc) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
