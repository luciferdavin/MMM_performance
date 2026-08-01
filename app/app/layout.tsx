import type { Metadata } from 'next';
import { ClientSwitcher } from '@/components/client-switcher';
import { SiteNav } from '@/components/site-nav';
import './globals.css';

export const metadata: Metadata = {
  title: 'MMM Platform',
  description: 'AI-powered Marketing Mix Modeling for agencies',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900">
        <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
          <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between gap-4 px-6">
            <div className="flex items-center gap-6">
              <a href="/" className="flex items-center gap-2 text-base font-semibold tracking-tight text-slate-900">
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">
                  M
                </span>
                <span className="hidden sm:inline">MMM Platform</span>
              </a>
              <ClientSwitcher />
            </div>
            <SiteNav />
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
