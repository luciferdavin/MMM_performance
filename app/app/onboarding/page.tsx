'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/cn';

const STEPS = [
  { title: 'Create org', description: 'Organization & defaults' },
  { title: 'Add client', description: 'Your first client' },
  { title: 'Connect data', description: 'CSV or platform API' },
  { title: 'Train model', description: 'First model' },
  { title: 'Done', description: 'Success' },
] as const;

const PLATFORMS = [
  { name: 'Shopify', type: 'API', badge: 'Revenue source', available: true },
  { name: 'Meta Ads', type: 'API', badge: 'Marketing API v19+', available: true },
  { name: 'Google Ads', type: 'API', badge: 'OAuth2', available: true },
  { name: 'GA4', type: 'API', badge: 'Data API v1beta', available: true },
  { name: 'TikTok', type: 'API', badge: 'Marketing API v1.3', available: false },
] as const;

type StepKey = 'org' | 'client' | 'connect' | 'train' | 'done';
const STEP_ORDER: StepKey[] = ['org', 'client', 'connect', 'train', 'done'];

function Stepper({ current, onNavigate }: { current: number; onNavigate: (index: number) => void }) {
  return (
    <ol className="flex items-center gap-0" aria-label="Onboarding progress">
      {STEPS.map((step, i) => {
        const isDone = i < current;
        const isCurrent = i === current;
        return (
          <li key={step.title} className="flex items-center">
            {i > 0 && (
              <span className={cn('mx-2 h-px w-6 sm:w-10', i <= current ? 'bg-indigo-600' : 'bg-slate-200')} aria-hidden="true" />
            )}
            <button
              type="button"
              onClick={() => isDone && onNavigate(i)}
              disabled={!isDone}
              className={cn('flex flex-col items-center gap-1', isDone ? 'cursor-pointer' : 'cursor-default')}
            >
              <span
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full border text-sm font-semibold transition-colors',
                  isDone && 'border-indigo-600 bg-indigo-600 text-white',
                  isCurrent && 'border-indigo-600 bg-white text-indigo-600 ring-2 ring-indigo-200',
                  !isDone && !isCurrent && 'border-slate-200 bg-white text-slate-400',
                )}
              >
                {isDone ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  i + 1
                )}
              </span>
              <span className={cn('text-xs font-medium', isCurrent ? 'text-indigo-700' : isDone ? 'text-slate-600' : 'text-slate-400')}>
                {step.title}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

const inputClass = 'mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:outline-2 focus:outline-indigo-600';

export default function OnboardingPage() {
  const [stepIndex, setStepIndex] = useState(0);
  const stepKey = STEP_ORDER[stepIndex];

  const next = () => setStepIndex((i) => Math.min(i + 1, STEP_ORDER.length - 1));
  const back = () => setStepIndex((i) => Math.max(i - 1, 0));

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Set up your workspace</h1>
        <p className="mt-1 text-sm text-slate-500">Connect data and train your first model in under 15 minutes.</p>
      </div>

      <div className="flex justify-center">
        <Stepper current={stepIndex} onNavigate={setStepIndex} />
      </div>

      {stepKey === 'org' && (
        <Card>
          <CardHeader>
            <CardTitle>Create your organization</CardTitle>
            <CardDescription>Pre-filled from your account — edit as needed.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field id="agency-name" label="Agency name">
              <input id="agency-name" type="text" defaultValue="Acme Agency" className={inputClass} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="industry" label="Industry segment">
                <select id="industry" className={inputClass} defaultValue="ecommerce">
                  <option value="ecommerce">Ecommerce / DTC</option>
                  <option value="saas">B2B SaaS</option>
                  <option value="finance">Finance</option>
                  <option value="travel">Travel</option>
                  <option value="other">Other</option>
                </select>
              </Field>
              <Field id="currency" label="Default currency">
                <select id="currency" className={inputClass} defaultValue="USD">
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                </select>
              </Field>
            </div>
            <p className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
              AI insights provider defaults to <span className="font-medium text-slate-700">Ollama (self-hosted)</span>.
              Claude or OpenAI can be configured later in Settings.
            </p>
            <div className="flex justify-end">
              <Button onClick={next}>Continue</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {stepKey === 'client' && (
        <Card>
          <CardHeader>
            <CardTitle>Add your first client</CardTitle>
            <CardDescription>Each client gets its own data, models, and reports.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field id="client-name" label="Client name" hint="Required">
              <input id="client-name" type="text" placeholder="e.g. Acme DTC" className={inputClass} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="client-domain" label="Domain" hint="Optional">
                <input id="client-domain" type="text" placeholder="acme-dtc.com" className={inputClass} />
              </Field>
              <Field id="client-currency" label="Currency">
                <select id="client-currency" className={inputClass} defaultValue="USD">
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                </select>
              </Field>
            </div>
            <div className="flex items-center justify-between gap-3">
              <button type="button" onClick={next} className="text-sm font-medium text-slate-500 hover:text-slate-700">
                Add another client later
              </button>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={back}>Back</Button>
                <Button onClick={next}>Save &amp; continue</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {stepKey === 'connect' && (
        <Card>
          <CardHeader>
            <CardTitle>Connect data source</CardTitle>
            <CardDescription>MMM needs spend and revenue data. CSV upload is fastest for a first run.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-6 text-center">
              <p className="text-sm font-medium text-slate-700">Upload a CSV (recommended)</p>
              <p className="mt-1 text-xs text-slate-500">Drop a file here, or paste from clipboard. Template with the canonical schema included.</p>
              <div className="mt-3 flex justify-center gap-2">
                <Button size="sm">Download template</Button>
                <Button size="sm" variant="secondary">Choose file</Button>
              </div>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-slate-700">Or connect a platform API</p>
              <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                {PLATFORMS.map((p) => (
                  <li key={p.name} className={cn('flex items-center justify-between gap-3 px-4 py-3', !p.available && 'opacity-50')}>
                    <div>
                      <p className="text-sm font-medium text-slate-900">{p.name}</p>
                      <p className="text-xs text-slate-500">{p.type} · {p.badge}</p>
                    </div>
                    {p.available ? (
                      <Button size="sm" variant="outline">Connect</Button>
                    ) : (
                      <Badge variant="secondary">Coming soon</Badge>
                    )}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={back}>Back</Button>
              <Button onClick={next}>Save &amp; continue</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {stepKey === 'train' && (
        <Card>
          <CardHeader>
            <CardTitle>Train your first model</CardTitle>
            <CardDescription>Recommended defaults are pre-selected — no tuning needed for the first run.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field id="model-name" label="Model name">
              <input id="model-name" type="text" defaultValue="First model — Acme" className={inputClass} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="date-start" label="Date range start">
                <input id="date-start" type="text" defaultValue="Mar 1, 2026" className={inputClass} />
              </Field>
              <Field id="date-end" label="Date range end">
                <input id="date-end" type="text" defaultValue="Jun 30, 2026" className={inputClass} />
              </Field>
            </div>
            <div className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
              Engine: <span className="font-medium text-slate-700">PyMC-Marketing (Bayesian)</span> · Priors: industry (ecommerce) · Adstock: geometric · Saturation: Hill · Sampler: NUTS · 4 chains × 500 draws.
              <span className="mt-1 block text-indigo-600">Advanced model settings (optional) — collapsed</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-slate-400">This run uses 1 of your 20 monthly model trains.</p>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={back}>Back</Button>
                <Button onClick={next}>Train my first model</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {stepKey === 'done' && (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100 text-green-600">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </span>
            <div>
              <h2 className="text-xl font-semibold text-slate-900">You trained your first MMM in ~4 min</h2>
              <p className="mt-2 text-sm text-slate-500">
                5 channels measured · Top channel: Meta (34% of revenue) · R&sup2; 0.84
              </p>
            </div>
            <ul className="w-full max-w-sm space-y-2 text-sm text-slate-600">
              <li className="rounded-md bg-slate-50 px-3 py-2">Channels measured across spend and revenue data</li>
              <li className="rounded-md bg-slate-50 px-3 py-2">Convergence check passed (R-hat 1.01)</li>
              <li className="rounded-md bg-slate-50 px-3 py-2">Model R&sup2; 0.84 — good fit</li>
            </ul>
            <div className="flex flex-wrap justify-center gap-2">
              <a href="/optimize"><Button>Run budget optimizer</Button></a>
              <a href="/reports"><Button variant="secondary">Generate executive report</Button></a>
              <a href="/"><Button variant="ghost">Back to dashboard</Button></a>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
