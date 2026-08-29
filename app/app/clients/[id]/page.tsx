import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { clients as clientsApi, models as modelsApi, type Client, type ModelJob, type ChannelContribution } from "@/lib/api";
import { formatDate, formatPercent, formatRoas } from "@/lib/format";
import { channelColor, channelLabel } from "@/lib/channel-colors";
import { cn } from "@/lib/cn";
import type { BadgeVariant } from "@/components/ui/badge";

const STATUS_META: Record<string, { label: string; variant: BadgeVariant }> = {
  queued: { label: "Queued", variant: "info" },
  running: { label: "Running", variant: "default" },
  succeeded: { label: "Completed", variant: "success" },
  failed: { label: "Failed", variant: "error" },
};

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums tracking-tight text-slate-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function ChannelPerformanceCard({ channel }: { channel: ChannelContribution }) {
  const color = channelColor(channel.channel);
  return (
    <div className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <span className="mt-0.5 h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-semibold text-slate-900">{channelLabel(channel.channel)}</span>
          <span className="tabular-nums text-sm font-bold text-slate-900">{formatRoas(channel.roas)} ROAS</span>
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

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

export default async function ClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let client: Client | null = null;
  let jobs: ModelJob[] = [];
  let latestContribs: ChannelContribution[] = [];
  let latestR2: number | null = null;
  let latestMape: number | null = null;

  try {
    client = await clientsApi.get(id);
    jobs = await modelsApi.list();
    jobs = jobs.filter((j) => j.client_id === id);
    const latest = jobs.find((j) => j.status === "succeeded");
    if (latest) {
      latestR2 = latest.r2 ?? null;
      latestMape = latest.mape ?? null;
      const contribs = await modelsApi.contributions(latest.id);
      latestContribs = contribs.sort((a, b) => b.roas - a.roas);
    }
  } catch {
    client = null;
  }

  if (!client) notFound();

  const topChannel = latestContribs[0];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <a href="/clients" className="hover:text-indigo-600 hover:underline">Clients</a>
            <span>/</span>
            <span className="text-slate-700">{client.name}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-baseline gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{client.name}</h1>
            <Badge variant="secondary">{client.slug}</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <a href="/onboarding"><Button variant="secondary">Train model</Button></a>
          <a href="/optimize"><Button>Run optimizer</Button></a>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {latestR2 !== null ? (
          <>
            <KpiCard label="Models trained" value={String(jobs.length)} sub="In this org" />
            <KpiCard label="R&sup2;" value={latestR2.toFixed(2)} sub="Fit quality" />
            <KpiCard label="MAPE" value={formatPercent(latestMape ?? 0)} sub="Prediction error" />
            <KpiCard
              label="Top channel"
              value={topChannel ? `${channelLabel(topChannel.channel)} ${formatPercent(topChannel.share)}` : "—"}
              sub="Share of revenue"
            />
          </>
        ) : (
          ["Models", "R²", "MAPE", "Top channel"].map((label) => (
            <KpiCard key={label} label={label} value="—" sub="Train a model to see KPIs" />
          ))
        )}
      </div>

      {/* Latest model + optimizer CTA */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle>Models</CardTitle>
            <CardDescription>All training runs for this client (most recent first).</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {jobs.length > 0 ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Model</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>R&sup2;</TableHead>
                      <TableHead>MAPE</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobs.map((m) => (
                      <TableRow key={m.id}>
                        <TableCell className="font-medium text-slate-900">
                          <a href={`/models/${m.id}`} className="text-indigo-600 hover:underline">{m.name}</a>
                        </TableCell>
                        <TableCell className="text-slate-500">{m.created_at ? formatDate(m.created_at) : "—"}</TableCell>
                        <TableCell className="font-mono tabular-nums text-slate-700">{m.r2 != null ? m.r2.toFixed(2) : "—"}</TableCell>
                        <TableCell className="font-mono tabular-nums text-slate-700">{m.mape != null ? formatPercent(m.mape) : "—"}</TableCell>
                        <TableCell>
                          <Badge variant={STATUS_META[m.status]?.variant ?? "secondary"}>
                            {STATUS_META[m.status]?.label ?? m.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <a href={`/models/${m.id}`}><Button variant="ghost" size="sm">Open</Button></a>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <EmptyState title="No models yet" description="Train your first model for this client." actions={<a href="/onboarding"><Button>Train model</Button></a>} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle>Budget optimizer</CardTitle>
            <CardDescription>Reallocate budget with what-if scenarios.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {latestR2 !== null ? (
              <>
                <p className="text-sm text-slate-600">
                  Optimize against <span className="font-medium text-slate-900">{client.name}</span> using its latest model.
                </p>
                <a href="/optimize"><Button className="w-full">Run budget optimizer</Button></a>
              </>
            ) : (
              <p className="text-sm text-slate-600">Run or complete a model before optimizing budgets.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Channel performance */}
      {latestContribs.length > 0 ? (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Channel performance</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {latestContribs.map((ch) => (
              <ChannelPerformanceCard key={ch.channel} channel={ch} />
            ))}
          </div>
        </div>
      ) : (
        <EmptyState title="No channel performance yet" description="Channel performance appears after a model finishes training." />
      )}

      {/* Quick actions */}
      <Card>
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle>Quick actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <a href="/connectors"><Button>Connect data source</Button></a>
          <a href="/onboarding"><Button variant="secondary">Train model</Button></a>
          <a href="/optimize"><Button variant="secondary">Run optimizer</Button></a>
          <a href="/reports"><Button variant="secondary">Generate report</Button></a>
        </CardContent>
      </Card>
    </div>
  );
}
