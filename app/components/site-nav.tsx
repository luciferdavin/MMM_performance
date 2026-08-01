'use client';

import { usePathname } from 'next/navigation';
import { cn } from '@/lib/cn';

const LINKS = [
  { href: '/', label: 'Dashboard' },
  { href: '/clients', label: 'Clients' },
  { href: '/connectors', label: 'Connectors' },
  { href: '/models', label: 'Models' },
  { href: '/optimize', label: 'Optimize' },
  { href: '/reports', label: 'Reports' },
  { href: '/onboarding', label: 'Onboarding' },
  { href: '/settings', label: 'Settings' },
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav className="hidden items-center gap-1 md:flex" aria-label="Main navigation">
      {LINKS.map((link) => {
        const isActive =
          link.href === '/' ? pathname === '/' : pathname.startsWith(link.href);
        return (
          <a
            key={link.href}
            href={link.href}
            className={cn(
              'rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-indigo-50 text-indigo-700'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
            )}
          >
            {link.label}
          </a>
        );
      })}
    </nav>
  );
}
