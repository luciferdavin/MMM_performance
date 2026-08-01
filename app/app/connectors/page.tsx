'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CONNECTORS, CLIENTS } from '@/lib/mock-data';
import { formatRelative, formatNumber } from '@/lib/format';
import type { ConnectorStatus } from '@/lib/mock-data';

const STATUS_META: Record<ConnectorStatus, { label: string; variant: 'success' | 'error' | 'info' | 'secondary' }> = {
  connected: { label: 'Connected', variant: 'success' },
  syncing: { label: 'Syncing', variant: 'info' },
  error: { label: 'Needs attention', variant: 'error' },
  'not-configured': { label: 'Not configured', variant: 'secondary' },
};

export default function ConnectorsPage() {
  const [clientId, setClientId] = useState<string>('all');

  const filtered = clientId === 'all'
    ? CONNECTORS
    : CONNECTORS.filter((c) => c.clientId === clientId);

  const clientName = (id: string) => CLIENTS.find((c) => c.id === id)?.name ?? id;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Data connectors</h1>
          <p className="mt-1 text-sm text-slate-500">Connected marketing and revenue sources per client.</p>
        </div>
        <Button>Connect new source</Button>
      </div>

      <div className="flex items-center gap-3">
        <label htmlFor="connector-client-filter" className="text-sm font-medium text-slate-600">Client</label>
        <select
          id="connector-client-filter"
          value={clientId}
          onChange={(e) => setClientId(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm focus:outline-2 focus:outline-indigo-600"
        >
          <option value="all">All clients</option>
          {CLIENTS.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <span className="text-sm text-slate-500">{filtered.length} source{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      <Card>
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle>Connected sources</CardTitle>
          <CardDescription>Manage data connections for each client.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState
              title="No connectors yet"
              description="No data sources connected. MMM needs spend and revenue data to build models."
              actions={<Button>Connect data source</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Connector</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last sync</TableHead>
                    <TableHead>Next sync</TableHead>
                    <TableHead>Rows</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((conn) => {
                    const meta = STATUS_META[conn.status];
                    return (
                      <TableRow key={conn.id}>
                        <TableCell className="font-medium text-slate-900">{conn.name}</TableCell>
                        <TableCell className="text-slate-600">{clientName(conn.clientId)}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">{conn.type}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                        </TableCell>
                        <TableCell className="text-slate-500">
                          {conn.lastSync ? formatRelative(conn.lastSync) : '—'}
                        </TableCell>
                        <TableCell className="text-slate-500">{conn.nextSync}</TableCell>
                        <TableCell className="tabular-nums text-slate-600">{formatNumber(conn.rowsFetched)}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm">Configure</Button>
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
