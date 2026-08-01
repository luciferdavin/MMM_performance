'use client';

import { useEffect, useRef, useState } from 'react';
import { CLIENTS } from '@/lib/mock-data';
import { cn } from '@/lib/cn';

function initials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

const STATUS_DOT: Record<string, string> = {
  healthy: 'bg-green-500',
  'needs-data': 'bg-slate-400',
  'retrain-due': 'bg-amber-500',
};

export function ClientSwitcher() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
      >
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-semibold text-indigo-700">
          {initials(CLIENTS[0]?.name ?? 'A')}
        </span>
        <span className="hidden sm:inline">{CLIENTS[0]?.name ?? 'Select client'}</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className={cn('h-4 w-4 text-slate-400 transition-transform', open && 'rotate-180')}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <ul role="listbox" aria-label="Switch client" className="absolute left-0 top-full z-50 mt-1 w-72 rounded-lg border border-slate-200 bg-white p-1 shadow-lg">
          <li className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 select-none">
            Clients
          </li>
          {CLIENTS.map((c) => (
            <li key={c.id}>
              <a
                href={`/clients/${c.id}`}
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-700 transition-colors hover:bg-slate-50"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">
                  {initials(c.name)}
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block truncate font-medium text-slate-900">{c.name}</span>
                  <span className="block truncate text-xs text-slate-500">{c.industry}</span>
                </span>
                <span className={cn('h-2 w-2 shrink-0 rounded-full', STATUS_DOT[c.status])} />
              </a>
            </li>
          ))}
          <li className="mt-1 border-t border-slate-100 pt-1">
            <a
              href="/clients"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-indigo-600 transition-colors hover:bg-indigo-50"
            >
              + Add client
            </a>
          </li>
        </ul>
      )}
    </div>
  );
}
