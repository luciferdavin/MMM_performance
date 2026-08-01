import { notFound } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EmptyState } from '@/components/ui/empty-state';
import { getClient, latestModel, recentModels, clientConnectors } from '@/lib/mock-data';
import { formatDate, formatCurrency, formatPercent, formatRoas } from '@/lib/format';
import { channelColor, channelLabel } from '@/lib/channel-colors';
import { cn } from '@/lib/cn';
import type { BadgeVariant } from '@/components/ui/badge';

const CLIENT_STATUS: Record<string, { label: string; variant: BadgeVariant }> = {
  healthy: { label: 'Healthy', variant: 'success' },
  'needs-data': { label: 'Needs data', variant: 'secondary' },
  'retrain-due': { label: 'Retrain due', variant: 'warning' },
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

function ChannelPerformanceCard({ channel }: { channel: { name: string; contribution: number; roas: number; spend: number } }) {
  const color = channelColor(channel.name);
  return (
    <div className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <span className="mt-0.5 h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-semibold text-slate-900">{channelLabel(channel.name)}</span>
          <span className="tabular-nums text-sm font-bold text-slate-900">{formatRoas(channel.roas)} ROAS</span>
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
          <span>Spend {formatCurrency(channel.spend)}</span>
          <span aria-hidden="true">·</span>
          <span>{formatPercent(channel.contribution)} of revenue</span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full" style={{ width: `${channel.contribution}%`, backgroundColor: color }} />
        </div>
      </div>
    </div>
  );
}

export default async function ClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const client = getClient(id);
  if (!client) notFound();

  const statusMeta = CLIENT_STATUS[client.status];
  const model = latestModel(client.id);
  const models = recentModels(client.id, 5);
  const connectors = clientConnectors(client.id);
  const topChannel = model?.channels.slice().sort((a, b) => b.contribution - a.contribution)[0];

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
            <Badge variant={statusMeta.variant}>{statusMeta.label}</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {client.industry} · {client.domain} · {client.currency}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary">Edit</Button>
          <Button variant="destructive">Delete</Button>
        </div>
      </div>

      {/* KPIs */}
      {model && model.r2 !== null ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Revenue (period)" value={formatCurrency(1_240_000)} sub="↑ 8.2% vs prior period" />
          <KpiCard label="Total spend" value={formatCurrency(394_000)} sub="↑ 5.1% vs prior period" />
          <KpiCard label="Blended ROAS" value={formatRoas(3.2)} sub="↑ 0.3 vs prior period" />
          <KpiCard
            label="Top channel"
            value={topChannel ? `${channelLabel(topChannel.name)} ${formatPercent(topChannel.contribution)}` : '—'}
            sub="Share of revenue"
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {['Revenue', 'Spend', 'ROAS', 'Top channel'].map((label) => (
            <KpiCard key={label} label={label} value="—" sub="Train a model to see KPIs" />
          ))}
        </div>
      )}

      {/* Latest model + optimizer CTA */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle>Latest model</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {model && model.r2 !== null ? (
              <div className="divide-y divide-slate-100">
                <div className="flex flex-wrap items-center justify-between gap-4 p-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-900">{model.name}</span>
                      <span className="font-mono text-xs text-slate-500">{model.version}</span>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">Trained {formatDate(model.trainedAt)} · {model.dateRange}</p>
                  </div>
                  <Badge variant="success">Completed</Badge>
                </div>
                <div className="grid gap-4 p-4 sm:grid-cols-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">R&sup2;</p>
                    <p className={cn('mt-1 text-lg font-bold tabular-nums', model.r2 >= 0.7 ? 'text-green-600' : model.r2 >= 0.5 ? 'text-amber-600' : 'text-red-600')}>{model.r2.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">MAPE</p>
                    <p className="mt-1 text-lg font-bold tabular-nums text-slate-900">{formatPercent(model.mape ?? 0)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">R-hat</p>
                    <p className="mt-1 text-lg font-bold tabular-nums text-slate-900">{(model.rhat ?? 0).toFixed(2)}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 border-t border-slate-100 p-4">
                  <a href="/models/m-102"><Button variant="secondary" size="sm">View diagnostics</Button></a>
                  <a href="/onboarding"><Button variant="ghost" size="sm">Retrain</Button></a>
                </div>
              </div>
            ) : (
              <EmptyState
                title="No model yet"
                description="Connect data, then train your first model in minutes."
                actions={<a href="/onboarding"><Button>Train model</Button></a>}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle>Budget optimizer</CardTitle>
            <CardDescription>Reallocate budget with what-if scenarios.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {model && model.r2 !== null ? (
              <>
                <p className="text-sm text-slate-600">
                  Optimize against <span className="font-medium text-slate-900">{model.name}</span> ({model.version}) to maximize revenue or ROAS under your channel constraints.
                </p>
                <a href="/optimize"><Button className="w-full">Run budget optimizer</Button></a>
                <p className="text-xs text-slate-400">Based on {model.channels.length} measured channels.</p>
              </>
            ) : (
              <p className="text-sm text-slate-600">Run or complete a model before optimizing budgets.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Channel performance */}
      {model && model.channels.length > 0 ? (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Channel performance</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {model.channels.map((ch) => (
              <ChannelPerformanceCard key={ch.name} channel={ch} />
            ))}
          </div>
        </div>
      ) : (
        <EmptyState
          title="No channel performance yet"
          description="Channel performance appears after a model finishes training."
        />
      )}

      {/* Recent models */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Recent models</h2>
        {models.length > 0 ? (
          <Card>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Model</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>R&sup2;</TableHead>
                    <TableHead>MAPE</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {models.map((m) => (
                    <TableRow key={m.id}>
                      <TableCell className="font-medium text-slate-900">
                        <a href={`/models/${m.id}`} className="text-indigo-600 hover:underline">
                          {m.name} <span className="font-mono text-xs text-slate-500">{m.version}</span>
                        </a>
                      </TableCell>
                      <TableCell className="text-slate-500">{formatDate(m.trainedAt)}</TableCell>
                      <TableCell className="font-mono tabular-nums text-slate-700">{m.r2 !== null ? m.r2.toFixed(2) : '—'}</TableCell>
                      <TableCell className="font-mono tabular-nums text-slate-700">{m.mape !== null ? formatPercent(m.mape) : '—'}</TableCell>
                      <TableCell>
                        <Badge variant={m.status === 'completed' ? 'success' : m.status === 'failed' ? 'error' : m.status === 'running' ? 'default' : 'secondary'}>
                          {m.status.charAt(0).toUpperCase() + m.status.slice(1)}
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
          </Card>
        ) : (
          <Card>
            <EmptyState
              title="No models yet"
              description="Your training history will appear here."
              actions={<a href="/onboarding"><Button>Train your first model</Button></a>}
            />
          </Card>
        )}
      </div>

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

      {connectors.length === 0 && (
        <p className="text-xs text-slate-400">
          No data sources connected for {client.name}. {models.length} model{models.length !== 1 ? 's' : ''} in history.
        </p>
      )}
    </div>
  );
}
