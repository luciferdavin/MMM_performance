import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { CLIENTS } from '@/lib/mock-data';

export default function OptimizePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Budget optimizer</h1>
        <p className="mt-1 text-sm text-slate-500">Reallocate budget across channels with what-if scenarios.</p>
      </div>

      <div className="flex items-center gap-3">
        <label htmlFor="opt-client" className="text-sm font-medium text-slate-600">Client</label>
        <select id="opt-client" className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm focus:outline-2 focus:outline-indigo-600">
          {CLIENTS.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        {/* Constraints panel */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Constraints</CardTitle>
            <CardDescription>Set total budget and per-channel limits.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label htmlFor="total-budget" className="block text-sm font-medium text-slate-700">Total weekly budget ($)</label>
              <input id="total-budget" type="number" defaultValue={50000} className="mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm tabular-nums text-slate-900 shadow-sm placeholder:text-slate-400 focus:outline-2 focus:outline-indigo-600" />
              <p className="mt-1 text-xs text-slate-400">Current plan spends $389k/month. Recommended total: $421k (+5%).</p>
            </div>
            <div className="space-y-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Channel constraints</p>
              {['Meta', 'Google Ads', 'TikTok', 'Organic', 'TV'].map((ch, i) => {
                const colors = ['#1877F2', '#EA4335', '#111111', '#14B8A6', '#8B5CF6'];
                return (
                  <div key={ch} className="flex items-center gap-3">
                    <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: colors[i] }} />
                    <span className="flex-1 text-sm text-slate-700">{ch}</span>
                    <span className="text-xs text-slate-400">0–100%</span>
                  </div>
                );
              })}
            </div>
            <Button className="w-full">Run optimization</Button>
          </CardContent>
        </Card>

        {/* Results panel */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Results</CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="Set constraints and run to see recommended allocation"
              description="Adjust your budget limits above, then click Run optimization."
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
