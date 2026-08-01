"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  clients as clientsApi,
  models as modelsApi,
  type Client,
  type FitResult,
  type MediaRecord,
} from "@/lib/api";
import { cn } from "@/lib/cn";

/* ------------------------------------------------------------------ */
/*  Types & constants                                                  */
/* ------------------------------------------------------------------ */

interface WizardState {
  orgName: string;
  clientName: string;
  createdClient: Client | null;
  connector: "csv" | "meta" | "google";
  fitResult: FitResult | null;
}

const TOTAL_STEPS = 5;

const STEPS = [
  { label: "Create organization" },
  { label: "Add first client" },
  { label: "Connect data" },
  { label: "Train model" },
  { label: "Done" },
] as const;

const CONNECTORS = [
  { value: "csv" as const, title: "CSV upload", desc: "Upload a spreadsheet of spend and revenue data" },
  { value: "meta" as const, title: "Meta Marketing API", desc: "Sync spend and performance from Meta Ads" },
  { value: "google" as const, title: "Google Ads API", desc: "Sync spend and performance from Google Ads" },
] as const;

/* ------------------------------------------------------------------ */
/*  Sample data (mirrors optimize page pattern)                         */
/* ------------------------------------------------------------------ */

function sampleRecords(): MediaRecord[] {
  const channels = ["meta", "google_ads", "tiktok", "tv", "radio"] as const;
  const base: Record<string, number> = { meta: 3000, google_ads: 2500, tiktok: 1500, tv: 1000, radio: 500 };
  const eff: Record<string, number> = { meta: 3.5, google_ads: 4.0, tiktok: 3.0, tv: 1.5, radio: 1.2 };
  const out: MediaRecord[] = [];
  for (let w = 0; w < 12; w++) {
    const d = new Date(Date.UTC(2026, 0, 5 + 7 * w)).toISOString().slice(0, 10);
    for (const ch of channels) {
      const spend = base[ch] * (1 + 0.1 * Math.sin(w));
      const revenue = spend * eff[ch] * 0.9;
      out.push({
        date: d,
        channel: ch,
        spend: +spend.toFixed(2),
        impressions: Math.round(spend * 1500),
        clicks: Math.round(spend * 30),
        conversions: Math.round(revenue / 80),
        revenue: +revenue.toFixed(2),
      });
    }
  }
  return out;
}

/* ------------------------------------------------------------------ */
/*  Step progress indicator                                             */
/* ------------------------------------------------------------------ */

function StepIndicator({ current }: { current: number }) {
  const progress = ((current) / (TOTAL_STEPS - 1)) * 100;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-900">
          Step {current + 1} of {TOTAL_STEPS}
        </span>
        <span className="text-slate-500">{STEPS[current].label}</span>
      </div>
      <Progress value={progress} />
      <ol className="flex items-center gap-2 sm:gap-4" aria-label="Onboarding progress">
        {STEPS.map((step, i) => {
          const isDone = i < current;
          const isCurrent = i === current;
          return (
            <li key={step.label} className="flex items-center">
              {i > 0 && (
                <span
                  className={cn(
                    "h-px flex-1",
                    i <= current ? "bg-indigo-600" : "bg-slate-200",
                  )}
                  aria-hidden="true"
                />
              )}
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                  isDone &&
                    "border-indigo-600 bg-indigo-600 text-white",
                  isCurrent &&
                    "border-indigo-600 bg-indigo-50 text-indigo-700 ring-2 ring-indigo-200",
                  !isDone &&
                    !isCurrent &&
                    "border-slate-200 bg-white text-slate-400",
                )}
              >
                {isDone ? (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-3.5 w-3.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : (
                  i + 1
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared input style                                                  */
/* ------------------------------------------------------------------ */

const inputClass =
  "mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:outline-2 focus:outline-indigo-600";

/* ------------------------------------------------------------------ */
/*  Page component                                                      */
/* ------------------------------------------------------------------ */

export default function OnboardingPage() {
  const [step, setStep] = useState(0);

  // Wizard state
  const [orgName, setOrgName] = useState("My Agency");
  const [clientName, setClientName] = useState("");
  const [createdClient, setCreatedClient] = useState<Client | null>(null);
  const [connector, setConnector] = useState<"csv" | "meta" | "google">("csv");
  const [fitResult, setFitResult] = useState<FitResult | null>(null);

  // Async states
  const [isCreatingClient, setIsCreatingClient] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* ----- validation per step ----- */

  const canAdvance = useCallback((): boolean => {
    switch (step) {
      case 0:
        return orgName.trim().length > 0;
      case 1:
        return clientName.trim().length > 0 && !isCreatingClient;
      case 2:
        return true;
      case 3:
        return !isTraining;
      default:
        return false;
    }
  }, [step, orgName, clientName, isCreatingClient, isTraining]);

  /* ----- next step handler ----- */

  const goNext = useCallback(async () => {
    setError(null);

    // Step 1: create client via API
    if (step === 1 && clientName.trim()) {
      setIsCreatingClient(true);
      try {
        const created = await clientsApi.create({ name: clientName.trim() });
        setCreatedClient(created);
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Failed to create client",
        );
        setIsCreatingClient(false);
        return;
      }
      setIsCreatingClient(false);
    }

    // Step 3: train model with sample data
    if (step === 3 && !fitResult) {
      setIsTraining(true);
      try {
        const result = await modelsApi.train(
          {
            name: "onboarding-demo",
            draws: 100,
            tune: 100,
            chains: 1,
            adstock_max_lag: 4,
          },
          sampleRecords(),
        );
        setFitResult(result);
        if (result.status !== "ok") {
          setError(result.error ?? "Training did not complete successfully.");
        }
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Training failed",
        );
        setIsTraining(false);
        return;
      }
      setIsTraining(false);
    }

    setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
  }, [step, clientName, fitResult]);

  const goBack = () => {
    setError(null);
    setStep((s) => Math.max(s - 1, 0));
  };

  /* ---------------------------------------------------------------- */
  /*  Render                                                            */
  /* ---------------------------------------------------------------- */

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Set up your agency
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Connect data and train your first model in minutes.
        </p>
      </div>

      {/* Progress */}
      <StepIndicator current={step} />

      {/* Error banner */}
      {error && (
        <div
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {/* -------- Step 0: Create organization -------- */}
      {step === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Create your organization</CardTitle>
            <CardDescription>
              Name your agency. This is shown on reports shared with clients.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label
                htmlFor="org-name"
                className="block text-sm font-medium text-slate-700"
              >
                Agency name
              </label>
              <input
                id="org-name"
                type="text"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && canAdvance() && goNext()}
                placeholder="e.g. Northbeam Media"
                className={inputClass}
              />
            </div>
            <div className="flex justify-end">
              <Button onClick={goNext} disabled={!canAdvance()}>
                Next
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* -------- Step 1: Add first client -------- */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Add your first client</CardTitle>
            <CardDescription>
              Each client gets its own data, models, and reports.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label
                htmlFor="client-name"
                className="block text-sm font-medium text-slate-700"
              >
                Client name
              </label>
              <input
                id="client-name"
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && canAdvance() && goNext()}
                placeholder="e.g. Acme DTC"
                className={inputClass}
              />
              <p className="mt-1 text-xs text-slate-400">Required</p>
            </div>

            {createdClient && (
              <div className="rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">
                Client <span className="font-medium">{createdClient.name}</span>{" "}
                created ({createdClient.slug}).
              </div>
            )}

            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={goNext}
                className="text-sm font-medium text-slate-500 hover:text-slate-700"
              >
                Add later
              </button>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={goBack}>
                  Back
                </Button>
                <Button onClick={goNext} disabled={!canAdvance()}>
                  {isCreatingClient ? "Creating..." : "Create & continue"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* -------- Step 2: Connect data -------- */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Connect a data source</CardTitle>
            <CardDescription>
              MMM needs spend and revenue data. Pick a connector -- full auth
              setup is coming soon.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <fieldset>
              <legend className="sr-only">Choose a data source</legend>
              <ul className="space-y-3">
                {CONNECTORS.map((c) => (
                  <li key={c.value}>
                    <label
                      className={cn(
                        "flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 transition-colors",
                        connector === c.value
                          ? "border-indigo-300 bg-indigo-50 ring-1 ring-indigo-200"
                          : "border-slate-200 bg-white hover:bg-slate-50",
                      )}
                    >
                      <input
                        type="radio"
                        name="connector"
                        value={c.value}
                        checked={connector === c.value}
                        onChange={() => setConnector(c.value)}
                        className="mt-0.5 accent-indigo-600"
                      />
                      <div>
                        <p className="text-sm font-medium text-slate-900">
                          {c.title}
                        </p>
                        <p className="text-xs text-slate-500">{c.desc}</p>
                      </div>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>

            <div className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
              For this onboarding demo we will train with embedded sample data.
              Real connector auth is on the roadmap.
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={goBack}>
                Back
              </Button>
              <Button onClick={goNext}>Next</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* -------- Step 3: Train demo model -------- */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Train a demo model</CardTitle>
            <CardDescription>
              Quick train on 12 weeks of sample data across 5 channels. Uses
              PyMC-Marketing with reduced draws for speed.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
              Engine:{" "}
              <span className="font-medium text-slate-700">
                PyMC-Marketing (Bayesian)
              </span>{" "}
              -- Adstock: geometric -- Saturation: Hill -- Sampler: NUTS -- 1
              chain x 100 draws.
            </div>

            {isTraining && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-indigo-700">
                  <svg
                    className="h-4 w-4 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Training model... this usually takes about a minute.
                </div>
                <Progress value={60} />
              </div>
            )}

            {fitResult && !isTraining && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  {fitResult.status === "ok" ? (
                    <Badge variant="success">Training succeeded</Badge>
                  ) : (
                    <Badge variant="error">Training incomplete</Badge>
                  )}
                </div>

                {fitResult.diagnostics && (
                  <ul className="grid gap-2 sm:grid-cols-3">
                    <li className="rounded-md bg-slate-50 px-3 py-2 text-sm">
                      <span className="text-xs text-slate-500 block">R&sup2;</span>
                      <span className="font-mono font-semibold text-slate-900">
                        {fitResult.diagnostics.r2.toFixed(3)}
                      </span>
                    </li>
                    <li className="rounded-md bg-slate-50 px-3 py-2 text-sm">
                      <span className="text-xs text-slate-500 block">MAPE</span>
                      <span className="font-mono font-semibold text-slate-900">
                        {(fitResult.diagnostics.mape * 100).toFixed(1)}%
                      </span>
                    </li>
                    <li className="rounded-md bg-slate-50 px-3 py-2 text-sm">
                      <span className="text-xs text-slate-500 block">
                        Converged
                      </span>
                      <span className="font-mono font-semibold text-slate-900">
                        {fitResult.diagnostics.converged ? "Yes" : "No"}
                      </span>
                    </li>
                  </ul>
                )}

                {fitResult.status === "ok" && (
                  <p className="text-xs text-slate-500">
                    Model ID: <span className="font-mono">{fitResult.model_id}</span>
                  </p>
                )}
              </div>
            )}

            <div className="flex items-center justify-between gap-3">
              {!fitResult && (
                <Button variant="secondary" onClick={goBack}>
                  Back
                </Button>
              )}

              <div className="flex gap-2 ml-auto">
                {!fitResult && (
                  <Button onClick={goNext} disabled={isTraining}>
                    {isTraining ? "Training..." : "Train demo model"}
                  </Button>
                )}
                {fitResult && fitResult.status === "ok" && (
                  <Button onClick={goNext}>Continue</Button>
                )}
                {fitResult && fitResult.status !== "ok" && (
                  <>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setFitResult(null);
                        setError(null);
                      }}
                    >
                      Retry
                    </Button>
                    <Button onClick={goNext}>Continue anyway</Button>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* -------- Step 4: Done -------- */}
      {step === 4 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-5 py-12 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100 text-green-600">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-7 w-7"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </span>

            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                Workspace ready
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Everything is set up and you are ready to go.
              </p>
            </div>

            {/* Summary list */}
            <ul className="w-full max-w-sm space-y-2 text-sm text-slate-600">
              <li className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
                <span>Organization</span>
                <span className="font-medium text-slate-900">{orgName}</span>
              </li>
              <li className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
                <span>Client</span>
                <span className="font-medium text-slate-900">
                  {createdClient ? createdClient.name : "Skipped"}
                </span>
              </li>
              <li className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
                <span>Data source</span>
                <span className="font-medium text-slate-900 capitalize">
                  {connector === "csv" ? "CSV upload" : connector}
                </span>
              </li>
              <li className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
                <span>Demo model</span>
                <span className="font-medium text-slate-900">
                  {fitResult
                    ? fitResult.status === "ok"
                      ? `R² ${fitResult.diagnostics?.r2.toFixed(2) ?? "--"}`
                      : "Not converged"
                    : "Skipped"}
                </span>
              </li>
            </ul>

            <div className="flex flex-wrap justify-center gap-2">
              <a href="/clients">
                <Button>Go to Clients</Button>
              </a>
              <a href="/optimize">
                <Button variant="secondary">Open Optimizer</Button>
              </a>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Footer nav (all steps except last) */}
      {step < TOTAL_STEPS - 1 && step !== 1 && step !== 3 && (
        <div className="flex justify-between">
          {step > 0 ? (
            <Button variant="ghost" onClick={goBack}>
              Back
            </Button>
          ) : (
            <span />
          )}
        </div>
      )}
    </div>
  );
}
