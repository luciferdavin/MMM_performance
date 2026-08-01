'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { MODELS, CLIENTS } from '@/lib/mock-data';
import { formatDate, formatPercent } from '@/lib/format';
import { cn } from '@/lib/cn';
import type { ModelStatus } from '@/lib/mock-data';

const STATUS_META: Record<ModelStatus, { label: string; variant: 'success' | 'error' | 'info' | 'default' | 'secondary' }> = {
  queued: { label: 'Queued', variant: 'info' },
  running: { label: 'Running', variant: 'default' },
  completed: { label: 'Completed', variant: 'success' },
  failed: { label: 'Failed', variant: 'error' },
  cancelled: { label: 'Cancelled', variant: 'secondary' },
};

const FILTERS = ['All', 'Running', 'Completed', 'Failed'] as const;
type Filter = (typeof FILTERS)[number];

export default function ModelsPage() {
  const [filter, setFilter] = useState<Filter>('All');

  const filtered = MODELS.filter((m) => {
    if (filter === 'All') return true;
    if (filter === 'Running') return m.status === 'running' || m.status === 'queued';
    return m.status.toLowerCase() === filter.toLowerCase();
  }).sort((a, b) => b.trainedAt.localeCompare(a.trainedAt));

  const clientName = (id: string) => CLIENTS.find((c) => c.id === id)?.name ?? id;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Model history</h1>
          <p className="mt-1 text-sm text-slate-500">All training jobs across clients.</p>
        </div>
        <a href="/onboarding">
          <Button>Train new model</Button>
        </a>
      </div>

      <div className="flex items-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={cn(
              'rounded-full border px-3 py-1 text-sm font-medium transition-colors',
              filter === f
                ? 'border-indigo-200 bg-indigo-50 text-indigo-700'
                : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
            )}
          >
            {f}
          </button>
        ))}
        <span className="ml-2 text-sm text-slate-500">{filtered.length} model{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState
              title="No models yet"
              description="Your training history will appear here. Connect data first, then train a model."
              actions={<a href="/onboarding"><Button>Train your first model</Button></a>}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Model</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>R&sup2;</TableHead>
                    <TableHead>MAPE</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((m) => {
                    const meta = STATUS_META[m.status];
                    return (
                      <TableRow key={m.id} className="group">
                        <TableCell>
                          <a
                            href={`/models/${m.id}`}
                            className="font-medium text-indigo-600 hover:underline"
                          >
                            {m.name}{' '}
                            <span className="font-mono text-xs text-slate-500">{m.version}</span>
                          </a>
                        </TableCell>
                        <TableCell className="text-slate-600">{clientName(m.clientId)}</TableCell>
                        <TableCell className="text-slate-500">{formatDate(m.trainedAt)}</TableCell>
                        <TableCell className={cn('tabular-nums font-mono text-sm', m.r2 !== null ? (m.r2 >= 0.7 ? 'text-green-600' : m.r2 >= 0.5 ? 'text-amber-600' : 'text-red-600') : 'text-slate-400')}>
                          {m.r2 !== null ? m.r2.toFixed(2) : '—'}
                        </TableCell>
                        <TableCell className={cn('tabular-nums font-mono text-sm', m.mape !== null ? (m.mape < 20 ? 'text-green-600' : 'text-amber-600') : 'text-slate-400')}>
                          {m.mape !== null ? formatPercent(m.mape) : '—'}
                        </TableCell>
                        <TableCell className="tabular-nums text-slate-500">{m.duration}</TableCell>
                        <TableCell>
                          {m.status === 'running' ? (
                            <div className="flex items-center gap-2">
                              <Badge variant={meta.variant}>{meta.label}</Badge>
                              <Progress value={45} className="w-16" />
                            </div>
                          ) : (
                            <Badge variant={meta.variant}>{meta.label}</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <a href={`/models/${m.id}`}>
                            <Button variant="ghost" size="sm">View</Button>
                          </a>
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
