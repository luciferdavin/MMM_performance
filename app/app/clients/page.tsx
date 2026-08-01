import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CLIENTS, latestModel, clientConnectors } from '@/lib/mock-data';
import { formatDate, formatPercent } from '@/lib/format';

const STATUS_MAP = {
  healthy: { label: 'Healthy', variant: 'success' as const },
  'needs-data': { label: 'Needs data', variant: 'secondary' as const },
  'retrain-due': { label: 'Retrain due', variant: 'warning' as const },
};

export default function ClientsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Clients</h1>
          <p className="mt-1 text-sm text-slate-500">{CLIENTS.length} client{CLIENTS.length !== 1 ? 's' : ''} in your workspace.</p>
        </div>
        <Button>+ Add client</Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {CLIENTS.length === 0 ? (
            <EmptyState
              title="No clients yet"
              description="Add your first client to start connecting data and measuring channel performance."
              actions={<Button>+ Add first client</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Client</TableHead>
                    <TableHead>Industry</TableHead>
                    <TableHead>Data sources</TableHead>
                    <TableHead>Latest model</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {CLIENTS.map((c) => {
                    const model = latestModel(c.id);
                    const conns = clientConnectors(c.id);
                    const st = STATUS_MAP[c.status];
                    return (
                      <TableRow key={c.id}>
                        <TableCell>
                          <a href={`/clients/${c.id}`} className="flex items-center gap-2 font-medium text-indigo-600 hover:underline">
                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">
                              {c.name.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()}
                            </span>
                            {c.name}
                          </a>
                        </TableCell>
                        <TableCell className="text-slate-600">{c.industry}</TableCell>
                        <TableCell>
                          {conns.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {conns.slice(0, 2).map((conn) => (
                                <Badge key={conn.id} variant="secondary">{conn.name.split(' ')[0]}</Badge>
                              ))}
                              {conns.length > 2 && <Badge variant="neutral">+{conns.length - 2}</Badge>}
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400">None</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {model && model.r2 !== null ? (
                            <span className="tabular-nums font-mono text-sm text-slate-700">
                              R&sup2; {model.r2.toFixed(2)} &middot; {formatDate(model.trainedAt)}
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400">No model</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant={st.variant}>{st.label}</Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <a href={`/clients/${c.id}`}><Button variant="ghost" size="sm">Open</Button></a>
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
