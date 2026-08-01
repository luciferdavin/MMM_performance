'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { MEMBERS } from '@/lib/mock-data';
import { cn } from '@/lib/cn';

const PROVIDERS = [
  {
    id: 'ollama',
    name: 'Ollama (self-hosted)',
    description: 'Default. Runs locally on your infrastructure. No external API costs, fully private.',
  },
  {
    id: 'claude',
    name: 'Claude',
    description: 'Anthropic API. Best narrative quality for executive reports and insights.',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    description: 'OpenAI API. Good general-purpose narrative generation.',
  },
] as const;

type ProviderId = (typeof PROVIDERS)[number]['id'];

const ROLE_VARIANTS = {
  Owner: 'default',
  Analyst: 'secondary',
  Viewer: 'neutral',
} as const;

function initials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export default function SettingsPage() {
  const [provider, setProvider] = useState<ProviderId>('ollama');

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Organization settings</h1>
        <p className="mt-1 text-sm text-slate-500">Workspace name, team, and AI provider configuration.</p>
      </div>

      {/* Organization name */}
      <Card>
        <CardHeader>
          <CardTitle>Organization</CardTitle>
          <CardDescription>Workspace name shown to your team and clients.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[240px]">
            <label htmlFor="org-name" className="block text-sm font-medium text-slate-700">Organization name</label>
            <input
              id="org-name"
              type="text"
              defaultValue="Acme Agency"
              className="mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:outline-2 focus:outline-indigo-600"
            />
          </div>
          <Button>Save changes</Button>
        </CardContent>
      </Card>

      {/* Members */}
      <Card>
        <CardHeader className="flex-row items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex flex-col gap-1">
            <CardTitle>Members</CardTitle>
            <CardDescription>{MEMBERS.length} people have access to this workspace.</CardDescription>
          </div>
          <Button size="sm">Invite member</Button>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {MEMBERS.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">
                          {initials(m.name)}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-slate-900">{m.name}</p>
                          <p className="text-xs text-slate-500">{m.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {m.role === 'Owner' ? (
                        <Badge variant="default">{m.role}</Badge>
                      ) : (
                        <select
                          defaultValue={m.role}
                          className="rounded-md border border-slate-200 bg-white px-2 py-1 text-sm text-slate-700 shadow-sm focus:outline-2 focus:outline-indigo-600"
                          aria-label={`Role for ${m.name}`}
                        >
                          <option>Analyst</option>
                          <option>Viewer</option>
                        </select>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={m.status === 'Active' ? 'success' : 'warning'}>{m.status}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {m.role === 'Owner' ? (
                        <span className="text-xs text-slate-400">Cannot remove</span>
                      ) : (
                        <Button variant="ghost" size="sm">Remove</Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* LLM provider */}
      <Card>
        <CardHeader>
          <CardTitle>AI insights provider</CardTitle>
          <CardDescription>Powers natural-language insights, reports, and Q&amp;A. If the provider is unreachable, template reports are used instead.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {PROVIDERS.map((p) => {
              const selected = provider === p.id;
              return (
                <label
                  key={p.id}
                  className={cn(
                    'flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors',
                    selected ? 'border-indigo-300 bg-indigo-50' : 'border-slate-200 bg-white hover:bg-slate-50',
                  )}
                >
                  <input
                    type="radio"
                    name="llm-provider"
                    value={p.id}
                    checked={selected}
                    onChange={() => setProvider(p.id)}
                    className="mt-0.5 h-4 w-4 accent-indigo-600"
                  />
                  <span className="flex-1">
                    <span className="block text-sm font-medium text-slate-900">{p.name}</span>
                    <span className="mt-0.5 block text-sm text-slate-500">{p.description}</span>
                  </span>
                  {p.id === 'ollama' && <Badge variant="default">Recommended</Badge>}
                </label>
              );
            })}
          </div>
          <div className="mt-4 flex justify-end">
            <Button>Save provider</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
