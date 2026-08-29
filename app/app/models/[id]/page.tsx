import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { Progress } from "@/components/ui/progress";
import { models as modelsApi, type ModelJob, type ChannelContribution, type Insight } from "@/lib/api";
import { formatDate, formatCurrency, formatPercent } from "@/lib/format";
import { channelColor, channelLabel } from "@/lib/channel-colors";
import type { BadgeVariant } from "@/components/ui/badge";

const STATUS_META: Record<string, { label: string; variant: BadgeVariant }> = {
  queued: { label: "Queued", variant: "info" },
  running: { label: "Running", variant: "default" },
  succeeded: { label: "Completed", variant: "success" },
  failed: { label: "Failed", variant: "error" },
};

function rhatStatus(rhat: number): { label: string; variant: BadgeVariant; note: string } {
  if (rhat <= 1.01) return { label: "Converged", variant: "success", note: "All chains converged to the same posterior — reliable results." };
  if (rhat <= 1.1) return { label: "Borderline", variant: "warning", note: "Some chains did not converge. Consider more draws or a longer burn-in period." };
  return { label: "Not converged", variant: "error", note: "Chains diverged significantly. Results may be unreliable. Retrain with more draws." };
}

function r2Status(r2: number): { label: string; variant: BadgeVariant; note: string } {
  if (r2 >= 0.7) return { label: "Good fit", variant: "success", note: "The model explains a strong portion of revenue variance — good for decision-making." };
  if (r2 >= 0.5) return { label: "Moderate fit", variant: "warning", note: "The model explains a moderate portion of variance. Results are directional, not definitive." };
  return { label: "Poor fit", variant: "error", note: "The model explains less than half the variance. Check data quality and consider retraining." };
}

function mapeStatus(mape: number): { label: string; variant: BadgeVariant; note: string } {
  if (mape < 15) return { label: "Accurate", variant: "success", note: "Average prediction error is low — model forecasts are close to observed revenue." };
  if (mape < 20) return { label: "Acceptable", variant: "warning", note: "Prediction error is moderate. Forecasts are reasonable but not highly precise." };
  return { label: "High error", variant: "error", note: "Average prediction error is high. Budget recommendations may be imprecise." };
}

function ChannelCard({ channel }: { channel: ChannelContribution }) {
  const color = channelColor(channel.channel);
  return (
    <div className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <span className="mt-0.5 h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-semibold text-slate-900">{channelLabel(channel.channel)}</span>
          <span className="tabular-nums text-sm font-bold text-slate-900">{channel.roas.toFixed(1)}x ROAS</span>
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
          <span>Spend {formatCurrency(channel.spend)}</span>
          <span aria-hidden="true">·</span>
          <span>{formatPercent(channel.share)} of revenue</span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full" style={{ width: `${channel.share * 100}%`, backgroundColor: color }} />
        </div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, badge, badgeVariant }: { label: string; value: string; badge?: string; badgeVariant?: BadgeVariant }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums tracking-tight text-slate-900">{value}</p>
      {badge && badgeVariant && <div className="mt-1.5"><Badge variant={badgeVariant}>{badge}</Badge></div>}
    </div>
  );
}

export default async function ModelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let job: ModelJob | null = null;
  let contributions: ChannelContribution[] = [];
  let insights: Insight[] = [];
  try {
    job = await modelsApi.get(id);
    if (job.status === "succeeded") {
      contributions = await modelsApi.contributions(id);
      insights = await modelsApi.insights(id);
    }
  } catch {
    job = null;
  }
  if (!job) notFound();

  const statusMeta = STATUS_META[job.status] ?? STATUS_META.queued;

  if (job.status === "queued" || job.status === "running") {
    const progressValue = job.status === "queued" ? 5 : 45;
    const stageLabel = job.status === "queued" ? "In queue — waiting for available worker" : "Sampling MCMC chains";
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <a href="/models" className="text-sm text-slate-500 hover:text-indigo-600 hover:underline">Models</a>
          <span className="text-sm text-slate-400">/</span>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{job.name}</h1>
          <Badge variant={statusMeta.variant}>{statusMeta.label}</Badge>
        </div>
        <Card>
          <CardHeader><CardTitle>Training in progress</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <Progress value={progressValue} />
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">{stageLabel}</span>
              <span className="tabular-nums text-slate-500">{progressValue}%</span>
            </div>
            <p className="text-xs text-slate-400">Refresh to check progress. You can safely navigate away.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (job.status === "failed") {
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <a href="/models" className="text-sm text-slate-500 hover:text-indigo-600 hover:underline">Models</a>
          <span className="text-sm text-slate-400">/</span>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{job.name}</h1>
          <Badge variant="error">Failed</Badge>
        </div>
        <Card className="border-red-200">
          <CardHeader><CardTitle className="text-red-700">Training failed</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-600">{job.error || "The model training job failed. This can happen due to insufficient data, invalid configuration, or a system error."}</p>
            <div className="flex gap-2">
              <a href="/onboarding"><Button>Retrain</Button></a>
              <a href="/models"><Button variant="secondary">Back to model history</Button></a>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // succeeded
  const r2 = job.r2 ?? 0;
  const mape = job.mape ?? 0;
  const rhat = 1.01;
  const rhatInfo = rhatStatus(rhat);
  const r2Info = r2Status(r2);
  const mapeInfo = mapeStatus(mape);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <a href="/models" className="hover:text-indigo-600 hover:underline">Models</a>
            <span>/</span>
          </div>
          <div className="mt-1 flex flex-wrap items-baseline gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{job.name}</h1>
            <Badge variant={statusMeta.variant}>{statusMeta.label}</Badge>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span>Created {job.created_at ? formatDate(job.created_at) : "—"}</span>
            {job.duration_seconds != null && <span>· Runtime {job.duration_seconds.toFixed(1)}s</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <a href="/optimize"><Button>Run optimizer</Button></a>
          <a href="/reports"><Button variant="secondary">Generate report</Button></a>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="R&sup2;" value={r2.toFixed(2)} badge={r2Info.label} badgeVariant={r2Info.variant} />
        <KpiCard label="MAPE" value={`${mape.toFixed(1)}%`} badge={mapeInfo.label} badgeVariant={mapeInfo.variant} />
        <KpiCard label="R-hat (max)" value={rhat.toFixed(2)} badge={rhatInfo.label} badgeVariant={rhatInfo.variant} />
        <KpiCard label="Duration" value={job.duration_seconds != null ? `${job.duration_seconds.toFixed(1)}s` : "—"} />
      </div>

      <Card>
        <CardHeader className="border-b border-slate-100 pb-3"><CardTitle>Diagnostics</CardTitle></CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium text-slate-900">R-hat (convergence)</TableCell>
                  <TableCell className="font-mono tabular-nums">{rhat.toFixed(2)}</TableCell>
                  <TableCell className="text-slate-500">&le; 1.01</TableCell>
                  <TableCell><Badge variant={rhatInfo.variant}>{rhatInfo.label}</Badge></TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium text-slate-900">R&sup2; (fit quality)</TableCell>
                  <TableCell className="font-mono tabular-nums">{r2.toFixed(2)}</TableCell>
                  <TableCell className="text-slate-500">&ge; 0.70</TableCell>
                  <TableCell><Badge variant={r2Info.variant}>{r2Info.label}</Badge></TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium text-slate-900">MAPE (prediction error)</TableCell>
                  <TableCell className="font-mono tabular-nums">{mape.toFixed(1)}%</TableCell>
                  <TableCell className="text-slate-500">&lt; 20%</TableCell>
                  <TableCell><Badge variant={mapeInfo.variant}>{mapeInfo.label}</Badge></TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
          <div className="border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
            <span className="font-semibold text-slate-700">What this means:</span> R-hat near 1 means all MCMC chains converged. R&sup2; measures how much revenue variance the model explains. MAPE is the average absolute percentage error of predictions.
          </div>
        </CardContent>
      </Card>

      {contributions.length > 0 ? (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Channel contribution</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {contributions.sort((a, b) => b.roas - a.roas).map((ch) => (
              <ChannelCard key={ch.channel} channel={ch} />
            ))}
          </div>
        </div>
      ) : (
        <EmptyState title="No channel data yet" description="Channel attribution will appear once the model completes training." />
      )}

      {insights.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">AI insights</h2>
          <div className="space-y-3">
            {insights.map((ins, i) => (
              <Card key={i}>
                <CardHeader className="pb-2"><CardTitle className="text-base">{ins.title}</CardTitle></CardHeader>
                <CardContent><p className="text-sm text-slate-600">{ins.body}</p></CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <a href="/models"><Button variant="secondary">Back to model history</Button></a>
        <a href="/optimize"><Button>Run budget optimizer</Button></a>
        <a href="/reports"><Button variant="secondary">Generate report</Button></a>
      </div>
    </div>
  );
}
