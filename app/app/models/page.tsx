"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  clients as clientsApi,
  models as modelsApi,
  type Client,
  type MediaRecord,
  type ModelConfig,
  type ModelJob,
  type ChannelContribution,
} from "@/lib/api";

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
        date: d,
        channel: ch,
        spend: +spend.toFixed(2),
        impressions: Math.round(spend * 1500),
        clicks: Math.round(spend * 30),
        conversions: Math.round(revenue / 80),
        revenue: +revenue.toFixed(2),
      });
    }
  }
  return out;
}

interface TrainedModel {
  modelId: string;
  modelName: string;
  status: string;
  r2: number | null;
  mape: number | null;
  trainedAt: Date;
}

export default function ModelsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const [training, setTraining] = useState(false);
  const [lastResult, setLastResult] = useState<{ model_job_id: string; status: string } | null>(null);
  const [models, setModels] = useState<TrainedModel[]>([]);
  const [contributions, setContributions] = useState<Record<string, ChannelContribution[]>>({});
  const [loadingContributions, setLoadingContributions] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshModels = useCallback(async () => {
    try {
      const data = await modelsApi.list();
      setModels(
        data.map((m) => ({
          modelId: m.id,
          modelName: m.name,
          status: m.status,
          r2: m.r2 ?? null,
          mape: m.mape ?? null,
          trainedAt: m.created_at ? new Date(m.created_at) : new Date(),
        }))
      );
    } catch {
      setModels([]);
    }
  }, []);

  useEffect(() => {
    clientsApi.list().then((data) => {
      setClients(data);
      if (data.length > 0) setSelectedClientId(data[0].id);
    }).catch(() => setClients([]));
    refreshModels();
  }, [refreshModels]);

  const train = useCallback(async () => {
    setTraining(true);
    setError(null);
    setLastResult(null);
    try {
      const fit = await modelsApi.train(
        { name: "mmm-model", draws: 100, tune: 100, chains: 1, adstock_max_lag: 4 },
        sampleRecords(),
        selectedClientId || undefined
      );
      setLastResult(fit);
      await refreshModels();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Training failed");
    } finally {
      setTraining(false);
    }
  }, [selectedClientId, refreshModels]);

  const loadContributions = useCallback(async (modelId: string) => {
    if (contributions[modelId]) return;
    setLoadingContributions(modelId);
    try {
      const data = await modelsApi.contributions(modelId);
      setContributions((prev) => ({ ...prev, [modelId]: data }));
    } catch (e) {
      console.error("Failed to load contributions:", e);
    } finally {
      setLoadingContributions(null);
    }
  }, [contributions]);

  const selectedClient = clients.find((c) => c.id === selectedClientId);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Models</h1>
          <p className="mt-1 text-sm text-slate-500">
            Train marketing mix models and view channel contributions.
          </p>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Train new model</CardTitle>
            <CardDescription>
              Select a client and train a new MMM model with sample data.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700">Client</label>
              <select
                value={selectedClientId}
                onChange={(e) => setSelectedClientId(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-2 focus:outline-indigo-600"
              >
                {clients.length === 0 && (
                  <option value="">No clients available</option>
                )}
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <Button
              onClick={train}
              disabled={training || clients.length === 0}
              className="w-full"
            >
              {training ? "Training model..." : "Train model"}
            </Button>

            {lastResult && (
              <div className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-700">Training Job</span>
                  <Badge variant={lastResult.status === "queued" || lastResult.status === "running" ? "info" : lastResult.status === "succeeded" ? "success" : "error"}>
                    {lastResult.status}
                  </Badge>
                </div>
                <div className="text-xs text-slate-500 font-mono">
                  Job ID: {lastResult.model_job_id}
                </div>
                <p className="text-xs text-slate-500">Training runs in the background. Refresh the list below or visit the model page to see results once complete.</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Training history</CardTitle>
            <CardDescription>
              All models trained in your organization (persisted across restarts).
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {models.length === 0 ? (
              <EmptyState
                title="No models trained yet"
                description="Train a model above to see it appear here."
              />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Model ID</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>R&sup2;</TableHead>
                      <TableHead>MAPE</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {models.map((m) => (
                      <TableRow key={m.modelId}>
                        <TableCell className="font-mono text-xs text-slate-600">
                          {m.modelId.slice(0, 8)}...
                        </TableCell>
                        <TableCell>
                          <Badge variant={m.status === "succeeded" ? "success" : m.status === "failed" ? "error" : "info"}>
                            {m.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="tabular-nums font-mono text-sm">
                          {m.r2 !== null ? (
                            <span className={m.r2 >= 0.7 ? "text-green-600" : "text-amber-600"}>
                              {m.r2.toFixed(3)}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </TableCell>
                        <TableCell className="tabular-nums font-mono text-sm">
                          {m.mape !== null ? (
                            <span className={m.mape < 20 ? "text-green-600" : "text-amber-600"}>
                              {m.mape.toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => loadContributions(m.modelId)}
                            disabled={loadingContributions === m.modelId}
                          >
                            {loadingContributions === m.modelId ? "Loading..." : "View contributions"}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {Object.entries(contributions).map(([modelId, contribs]) => (
        <Card key={modelId}>
          <CardHeader>
            <CardTitle>Channel contributions</CardTitle>
            <CardDescription>
              Model: {modelId.slice(0, 8)}... — Contribution breakdown by channel.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Channel</TableHead>
                    <TableHead className="text-right">Spend</TableHead>
                    <TableHead className="text-right">Contribution</TableHead>
                    <TableHead className="text-right">Share</TableHead>
                    <TableHead className="text-right">ROAS</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {contribs.map((c) => (
                    <TableRow key={c.channel}>
                      <TableCell className="font-medium text-slate-900">{c.channel}</TableCell>
                      <TableCell className="text-right tabular-nums text-slate-600">
                        ${c.spend.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-slate-600">
                        {c.contribution.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        <span className="text-slate-600">{(c.share * 100).toFixed(1)}%</span>
                        <div className="mt-1 h-1.5 w-16 bg-slate-100 rounded-full inline-block ml-2">
                          <div
                            className="h-1.5 bg-indigo-600 rounded-full"
                            style={{ width: `${c.share * 100}%` }}
                          />
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        <span className={c.roas >= 3 ? "text-green-600" : c.roas >= 1 ? "text-amber-600" : "text-red-600"}>
                          {c.roas.toFixed(2)}x
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
