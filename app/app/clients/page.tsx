"use client";

import { useEffect, useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { clients as clientsApi, type Client } from "@/lib/api";

export default function ClientsPage() {
  const [items, setItems] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await clientsApi.list());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load clients");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = async () => {
    if (!name.trim()) return;
    try {
      await clientsApi.create({ name: name.trim() });
      setName("");
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create client");
    }
  };

  const remove = async (id: string) => {
    try {
      await clientsApi.remove(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete client");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Clients</h1>
          <p className="mt-1 text-sm text-slate-500">
            {loading ? "Loading…" : `${items.length} client${items.length !== 1 ? "s" : ""} in your workspace.`}
          </p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>+ Add client</Button>
      </div>

      {showForm && (
        <Card className="max-w-md">
          <CardContent className="space-y-3 pt-5">
            <label className="block text-sm font-medium text-slate-700">Client name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && create()}
              placeholder="Acme DTC"
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <Button onClick={create} disabled={!name.trim()}>Create</Button>
          </CardContent>
        </Card>
      )}

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-sm text-slate-400">Loading clients…</div>
          ) : items.length === 0 ? (
            <EmptyState
              title="No clients yet"
              description="Add your first client to start connecting data and measuring channel performance."
              actions={<Button onClick={() => setShowForm(true)}>+ Add first client</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Client</TableHead>
                    <TableHead>Slug</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium text-slate-900">{c.name}</TableCell>
                      <TableCell className="text-slate-500">{c.slug}</TableCell>
                      <TableCell><Badge variant="success">connected</Badge></TableCell>
                      <TableCell className="text-right">
                        <button className="text-sm text-slate-400 hover:text-red-600" onClick={() => remove(c.id)}>
                          Remove
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
