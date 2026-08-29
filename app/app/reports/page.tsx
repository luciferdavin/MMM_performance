"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { reports as reportsApi, type MediaRecord } from "@/lib/api";

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
      out.push({ date: d, channel: ch, spend: +spend.toFixed(2), impressions: Math.round(spend * 1500), clicks: Math.round(spend * 30), conversions: Math.round(revenue / 80), revenue: +revenue.toFixed(2) });
    }
  }
  return out;
}

interface GeneratedReport {
  report_id: string;
  client_name?: string;
  markdown: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [generating, setGenerating] = useState(false);
  const [clientName, setClientName] = useState("Client");
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GeneratedReport | null>(null);

  const refresh = async () => {
    try {
      const list = await reportsApi.list();
      setReports((prev) => [
        ...prev,
        ...list.map((r) => ({ report_id: r.report_id, client_name: r.client_name, markdown: "" })),
      ]);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const generate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const report = await reportsApi.generate({
        records: sampleRecords(),
        config: { name: "report-demo", draws: 100, tune: 100, chains: 1, adstock_max_lag: 4 },
        client_name: clientName || "Client",
        total_budget: 50000,
      });
      setReports((prev) => [report, ...prev]);
      setSelected(report);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Reports</h1>
          <p className="mt-1 text-sm text-slate-500">Auto-generated MMM reports with AI insights.</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
            placeholder="Client name"
            className="w-40 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:outline-2 focus:outline-indigo-600"
          />
          <Button onClick={generate} disabled={generating}>
            {generating ? "Generating…" : "Generate report"}
          </Button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Reports</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {reports.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  title="No reports yet"
                  description="Generate an executive report from your latest model to share with clients."
                  actions={<Button onClick={generate} disabled={generating}>Generate report</Button>}
                />
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {reports.map((r) => (
                  <li key={r.report_id} className="flex items-center justify-between px-4 py-3">
                    <button
                      className="text-sm font-medium text-slate-900 hover:text-indigo-600"
                      onClick={async () => {
                        if (r.markdown) {
                          setSelected(r);
                          return;
                        }
                        try {
                          const full = await reportsApi.get(r.report_id);
                          const updated = { ...r, markdown: full.markdown };
                          setReports((prev) => prev.map((x) => (x.report_id === r.report_id ? updated : x)));
                          setSelected(updated);
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Failed to load report");
                        }
                      }}
                    >
                      {r.client_name} — report
                    </button>
                    <a href={reportsApi.pdfUrl(r.report_id)} target="_blank" rel="noopener noreferrer" className="text-sm text-indigo-600 hover:underline">
                      PDF
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{selected ? `${selected.client_name} — Report` : "Report preview"}</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[70vh] overflow-y-auto">
            {!selected && <p className="text-sm text-slate-400">Select or generate a report to preview.</p>}
            {selected && (
              <div className="prose prose-sm max-w-none whitespace-pre-wrap text-sm text-slate-700">
                {selected.markdown}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
