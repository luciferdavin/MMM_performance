import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EmptyState } from '@/components/ui/empty-state';
import { CLIENTS, latestModel } from '@/lib/mock-data';
import { formatDate, formatPercent } from '@/lib/format';
import { channelColor, channelLabel } from '@/lib/channel-colors';

export default function DashboardPage() {
  const modelTrains30d = 47;
  const avgR2 = 0.84;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Agency dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">Cross-client overview and recent activity.</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Active clients', value: String(CLIENTS.length), sub: '+2 this month' },
          { label: 'Models trained (30d)', value: String(modelTrains30d), sub: '47 / 100 quota' },
          { label: 'Avg. model R²', value: avgR2.toFixed(2), sub: 'Above 0.70 target' },
          { label: 'Insights (30d)', value: '124', sub: '5 reports shared' },
        ].map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums tracking-tight text-slate-900">{kpi.value}</p>
            <p className="mt-1 text-xs text-slate-500">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* Client overview */}
      {CLIENTS.length === 0 ? (
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
                    <TableHead>Industry</TableHead>
                    <TableHead>Latest model</TableHead>
                    <TableHead>Top channel</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {CLIENTS.map((c) => {
                    const model = latestModel(c.id);
                    const topCh = model?.channels.slice().sort((a, b) => b.contribution - a.contribution)[0];
                    return (
                      <TableRow key={c.id}>
                        <TableCell>
                          <a href={`/clients/${c.id}`} className="font-medium text-indigo-600 hover:underline">
                            {c.name}
                          </a>
                        </TableCell>
                        <TableCell className="text-slate-600">{c.industry}</TableCell>
                        <TableCell>
                          {model && model.r2 !== null ? (
                            <span className="tabular-nums font-mono text-sm text-slate-700">R&sup2; {model.r2.toFixed(2)} &middot; {formatDate(model.trainedAt)}</span>
                          ) : (
                            <span className="text-xs text-slate-400">No model</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {topCh ? (
                            <span className="flex items-center gap-1.5 text-sm text-slate-700">
                              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: channelColor(topCh.name) }} />
                              {channelLabel(topCh.name)} {formatPercent(topCh.contribution)}
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant={c.status === 'healthy' ? 'success' : c.status === 'needs-data' ? 'secondary' : 'warning'}>
                            {c.status === 'healthy' ? 'Healthy' : c.status === 'needs-data' ? 'Needs data' : 'Retrain due'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <a href="/onboarding"><Button variant="ghost" size="sm">Train</Button></a>
                            <a href="/optimize"><Button variant="ghost" size="sm">Optimize</Button></a>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
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
