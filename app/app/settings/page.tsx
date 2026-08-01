"use client";

import { useEffect, useRef, useState } from "react";
import type { BadgeVariant } from "@/components/ui/badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/cn";

const PLAN_TIERS = ["Starter", "Pro", "Enterprise"] as const;
type PlanTier = (typeof PLAN_TIERS)[number];

const PROVIDERS = [
  {
    id: "ollama",
    name: "Ollama",
    description:
      "Self-hosted default. Runs locally on your infrastructure — no external API costs and fully private.",
  },
  {
    id: "claude",
    name: "Claude",
    description: "Anthropic API. Best narrative quality for executive reports and insights.",
  },
  {
    id: "openai",
    name: "OpenAI",
    description: "OpenAI API. Good general-purpose narrative generation.",
  },
] as const;

type ProviderId = (typeof PROVIDERS)[number]["id"];

type MemberRole = "agency_owner" | "analyst" | "viewer";

interface Member {
  id: string;
  name: string;
  email: string;
  role: MemberRole;
}

const SEED_MEMBERS: Member[] = [
  { id: "u1", name: "Ari Patel", email: "ari@acmeagency.io", role: "agency_owner" },
  { id: "u2", name: "Sam Torres", email: "sam@acmeagency.io", role: "analyst" },
  { id: "u3", name: "Jin Lee", email: "jin@acmeagency.io", role: "analyst" },
  { id: "u4", name: "Casey Chen", email: "casey@acmeagency.io", role: "viewer" },
];

const ROLE_VARIANTS: Record<MemberRole, BadgeVariant> = {
  agency_owner: "default",
  analyst: "info",
  viewer: "secondary",
};

const ROLE_LABELS: Record<MemberRole, string> = {
  agency_owner: "Agency owner",
  analyst: "Analyst",
  viewer: "Viewer",
};

function initials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export default function SettingsPage() {
  const [orgName, setOrgName] = useState("Acme Agency");
  const [plan] = useState<PlanTier>("Pro");
  const [members] = useState<Member[]>(SEED_MEMBERS);

  const [provider, setProvider] = useState<ProviderId>("ollama");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const [profileSaved, setProfileSaved] = useState(false);
  const [providerSaved, setProviderSaved] = useState(false);

  const profileTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const providerTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (profileTimer.current) clearTimeout(profileTimer.current);
      if (providerTimer.current) clearTimeout(providerTimer.current);
    };
  }, []);

  const saveProfile = () => {
    if (profileTimer.current) clearTimeout(profileTimer.current);
    setProfileSaved(true);
    profileTimer.current = setTimeout(() => setProfileSaved(false), 3200);
  };

  const saveProvider = () => {
    if (providerTimer.current) clearTimeout(providerTimer.current);
    setProviderSaved(true);
    providerTimer.current = setTimeout(() => setProviderSaved(false), 3200);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">Organization profile, team access, and AI provider configuration.</p>
      </div>

      {/* Organization profile */}
      <Card>
        <CardHeader>
          <CardTitle>Organization profile</CardTitle>
          <CardDescription>Workspace name and plan tier shown to your team and clients.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="org-name" className="block text-sm font-medium text-slate-700">
                Organization name
              </label>
              <input
                id="org-name"
                type="text"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="Acme Agency"
                className="mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:outline-2 focus:outline-indigo-600"
              />
            </div>
            <div>
              <span className="block text-sm font-medium text-slate-700">Plan tier</span>
              <div className="mt-1.5 flex items-center gap-2">
                <Badge variant="default">{plan}</Badge>
                <span className="text-xs text-slate-500">
                  {PLAN_TIERS.map((t) => t).join(" · ")} — managed by your billing admin
                </span>
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-end gap-3">
            {profileSaved && (
              <span role="status" className="text-sm font-medium text-green-600">
                Profile saved.
              </span>
            )}
            <Button onClick={saveProfile} disabled={!orgName.trim()}>
              Save changes
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Team members */}
      <Card>
        <CardHeader>
          <CardTitle>Team members</CardTitle>
          <CardDescription>
            {members.length} member{members.length !== 1 ? "s" : ""} have access to this workspace.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {members.length === 0 ? (
            <EmptyState
              title="No team members"
              description="Invite teammates to collaborate on models, reports, and client data."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {members.map((m) => (
                    <TableRow key={m.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">
                            {initials(m.name)}
                          </span>
                          <span className="font-medium text-slate-900">{m.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-slate-500">{m.email}</TableCell>
                      <TableCell>
                        <Badge variant={ROLE_VARIANTS[m.role]}>{ROLE_LABELS[m.role]}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* LLM provider config */}
      <Card>
        <CardHeader>
          <CardTitle>AI insights provider</CardTitle>
          <CardDescription>
            Powers natural-language insights, reports, and Q&amp;A. Ollama (self-hosted) is the default and keeps your
            data on your infrastructure; if the provider is unreachable, template reports are used instead.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {PROVIDERS.map((p) => {
              const selected = provider === p.id;
              return (
                <label
                  key={p.id}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors",
                    selected ? "border-indigo-300 bg-indigo-50" : "border-slate-200 bg-white hover:bg-slate-50",
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
                  {p.id === "ollama" && <Badge variant="default">Default</Badge>}
                </label>
              );
            })}
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-end gap-3">
            {providerSaved && (
              <span role="status" className="text-sm font-medium text-green-600">
                Saved.
              </span>
            )}
            <Button onClick={saveProvider}>Save provider</Button>
          </div>
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Danger zone</CardTitle>
          <CardDescription>
            Irreversible actions for this organization. Use with care.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-slate-900">Delete organization</p>
              <p className="mt-0.5 text-sm text-slate-500">
                Permanently remove the organization, its clients, models, and reports.
              </p>
            </div>
            <Button variant="destructive" onClick={() => setConfirmDelete((v) => !v)}>
              Delete organization
            </Button>
          </div>
          {confirmDelete && (
            <p
              role="alert"
              className="mt-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600"
            >
              This action is not available yet — it is shown for preview only. When enabled, deleting the
              organization will permanently remove all clients, models, and reports.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
