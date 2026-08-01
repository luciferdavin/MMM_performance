-- =====================================================
-- MMM Platform -- Initial Schema Migration
-- Version: 001
-- Date: 2026-08-01
-- =====================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- ENUM TYPES
-- =====================================================

DO $$ BEGIN
  CREATE TYPE public.plan_tier AS ENUM ('starter', 'pro', 'enterprise');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.membership_role AS ENUM ('agency_owner', 'analyst', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.connector_type AS ENUM (
    'csv', 'meta_ads', 'google_ads', 'ga4', 'tiktok', 'shopify',
    'linkedin', 'snap', 'pinterest'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.job_status AS ENUM ('queued', 'running', 'succeeded', 'failed', 'canceled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.insight_source AS ENUM ('llm', 'template');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.report_status AS ENUM ('generating', 'ready', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.usage_record_type AS ENUM (
    'compute_seconds', 'storage_mb', 'api_calls', 'llm_tokens', 'model_train', 'sync_run'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE public.llm_provider AS ENUM ('ollama', 'openai', 'anthropic');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- HELPER FUNCTIONS (must precede RLS policies)
-- =====================================================

-- Helper: check if current user is a member of the given org
CREATE OR REPLACE FUNCTION public.is_org_member(org_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.memberships m
    WHERE m.organization_id = org_id AND m.user_id = auth.uid()
  );
$$;

-- Helper: check if current user has at least 'analyst' role in the org
CREATE OR REPLACE FUNCTION public.is_org_analyst_or_above(org_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.memberships m
    WHERE m.organization_id = org_id
      AND m.user_id = auth.uid()
      AND m.role IN ('agency_owner', 'analyst')
  );
$$;

-- Helper: check if current user is org owner
CREATE OR REPLACE FUNCTION public.is_org_owner(org_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.memberships m
    WHERE m.organization_id = org_id
      AND m.user_id = auth.uid()
      AND m.role = 'agency_owner'
  );
$$;

-- updated_at trigger function
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- =====================================================
-- TABLE: organizations
-- =====================================================

CREATE TABLE public.organizations (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name       text NOT NULL,
  slug       text NOT NULL,
  plan_tier  public.plan_tier NOT NULL DEFAULT 'starter',
  settings   jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_organizations_slug ON public.organizations (slug);
CREATE TRIGGER trg_organizations_updated_at
  BEFORE UPDATE ON public.organizations
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: users
-- =====================================================

CREATE TABLE public.users (
  id           uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email        text NOT NULL,
  full_name    text,
  avatar_url   text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz
);

CREATE UNIQUE INDEX idx_users_email ON public.users (email);

-- =====================================================
-- TABLE: memberships
-- =====================================================

CREATE TABLE public.memberships (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  role            public.membership_role NOT NULL DEFAULT 'analyst',
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_memberships_org_user UNIQUE (organization_id, user_id)
);

CREATE INDEX idx_memberships_org ON public.memberships (organization_id);
CREATE INDEX idx_memberships_user ON public.memberships (user_id);

-- =====================================================
-- TABLE: clients
-- =====================================================

CREATE TABLE public.clients (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  name            text NOT NULL,
  slug            text NOT NULL,
  industry        text,
  timezone        text NOT NULL DEFAULT 'America/New_York',
  currency        text NOT NULL DEFAULT 'USD',
  target_column   text NOT NULL DEFAULT 'revenue'
    CHECK (target_column IN ('revenue', 'conversions', 'clicks')),
  control_columns jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  archived        boolean NOT NULL DEFAULT false,
  CONSTRAINT uq_clients_org_slug UNIQUE (organization_id, slug)
);

CREATE INDEX idx_clients_org ON public.clients (organization_id);
CREATE INDEX idx_clients_org_active ON public.clients (organization_id) WHERE archived = false;
CREATE TRIGGER trg_clients_updated_at
  BEFORE UPDATE ON public.clients
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: data_sources
-- =====================================================

CREATE TABLE public.data_sources (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id      uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id            uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  connector_type       public.connector_type NOT NULL,
  name                 text NOT NULL,
  config               jsonb NOT NULL DEFAULT '{}'::jsonb,
  credentials_encrypted text,
  sync_schedule        text NOT NULL DEFAULT 'weekly',
  last_sync_at         timestamptz,
  sync_status          text NOT NULL DEFAULT 'idle',
  last_error           text,
  enabled              boolean NOT NULL DEFAULT true,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_data_sources_client_type_name UNIQUE (client_id, connector_type, name)
);

CREATE INDEX idx_data_sources_client ON public.data_sources (client_id);
CREATE INDEX idx_data_sources_org ON public.data_sources (organization_id);
CREATE INDEX idx_data_sources_sync_schedule ON public.data_sources (sync_schedule) WHERE enabled = true;
CREATE TRIGGER trg_data_sources_updated_at
  BEFORE UPDATE ON public.data_sources
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: marketing_data
-- Normalized connector output rows. Stores the raw data
-- ingested from each data source, normalized to a common
-- schema with date, channel, spend, impressions, clicks,
-- conversions, and revenue columns.
-- =====================================================

CREATE TABLE public.marketing_data (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  data_source_id  uuid NOT NULL REFERENCES public.data_sources(id) ON DELETE CASCADE,
  date            date NOT NULL,
  channel         text NOT NULL,
  spend           numeric(14,2) NOT NULL DEFAULT 0,
  impressions     bigint NOT NULL DEFAULT 0,
  clicks          bigint NOT NULL DEFAULT 0,
  conversions     bigint NOT NULL DEFAULT 0,
  revenue         numeric(14,2) NOT NULL DEFAULT 0,
  raw             jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_marketing_data_org ON public.marketing_data (organization_id);
CREATE INDEX idx_marketing_data_client ON public.marketing_data (client_id, date DESC);
CREATE INDEX idx_marketing_data_source ON public.marketing_data (data_source_id);
CREATE INDEX idx_marketing_data_date_channel ON public.marketing_data (client_id, date, channel);

-- =====================================================
-- TABLE: model_jobs
-- =====================================================

CREATE TABLE public.model_jobs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  name            text NOT NULL DEFAULT 'default',
  config          jsonb NOT NULL,
  status          public.job_status NOT NULL DEFAULT 'queued',
  diagnostics     jsonb,
  result_summary  jsonb,
  metrics         jsonb NOT NULL DEFAULT '{}'::jsonb,
  artifact_key    text,
  error           text,
  forecast_days   integer NOT NULL DEFAULT 90,
  queued_at       timestamptz NOT NULL DEFAULT now(),
  started_at      timestamptz,
  finished_at     timestamptz,
  created_by      uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (started_at IS NULL OR started_at >= queued_at),
  CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE INDEX idx_model_jobs_client_created ON public.model_jobs (client_id, created_at DESC);
CREATE INDEX idx_model_jobs_org_status ON public.model_jobs (organization_id, status);
CREATE INDEX idx_model_jobs_created_by ON public.model_jobs (created_by);
CREATE INDEX idx_model_jobs_active ON public.model_jobs (status) WHERE status IN ('queued', 'running');

-- =====================================================
-- TABLE: channel_results
-- =====================================================

CREATE TABLE public.channel_results (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  model_job_id    uuid NOT NULL REFERENCES public.model_jobs(id) ON DELETE CASCADE,
  channel         text NOT NULL,
  contribution    double precision NOT NULL,
  share           double precision NOT NULL CHECK (share >= 0 AND share <= 1),
  roas            double precision NOT NULL,
  spend           double precision NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_channel_results_job_channel UNIQUE (model_job_id, channel)
);

CREATE INDEX idx_channel_results_job ON public.channel_results (model_job_id);
CREATE INDEX idx_channel_results_client ON public.channel_results (client_id, created_at DESC);
CREATE INDEX idx_channel_results_org ON public.channel_results (organization_id);

-- =====================================================
-- TABLE: budget_optimizations
-- =====================================================

CREATE TABLE public.budget_optimizations (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id          uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id                uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  model_job_id             uuid NOT NULL REFERENCES public.model_jobs(id) ON DELETE CASCADE,
  constraints              jsonb NOT NULL,
  allocations              jsonb NOT NULL,
  total_budget             double precision NOT NULL CHECK (total_budget > 0),
  expected_total_revenue   double precision NOT NULL,
  is_feasible              boolean NOT NULL,
  created_by               uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  created_at               timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_budget_optimizations_job ON public.budget_optimizations (model_job_id);
CREATE INDEX idx_budget_optimizations_client ON public.budget_optimizations (client_id, created_at DESC);
CREATE INDEX idx_budget_optimizations_org ON public.budget_optimizations (organization_id);

-- =====================================================
-- TABLE: reports
-- =====================================================

CREATE TABLE public.reports (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  model_job_id    uuid NOT NULL REFERENCES public.model_jobs(id) ON DELETE CASCADE,
  title           text NOT NULL,
  content         text,
  status          public.report_status NOT NULL DEFAULT 'generating',
  pdf_key         text,
  share_token     uuid NOT NULL DEFAULT gen_random_uuid(),
  share_expires_at timestamptz,
  error           text,
  created_by      uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_reports_share_token ON public.reports (share_token);
CREATE INDEX idx_reports_client_created ON public.reports (client_id, created_at DESC);
CREATE INDEX idx_reports_org ON public.reports (organization_id);
CREATE INDEX idx_reports_model_job ON public.reports (model_job_id);
CREATE TRIGGER trg_reports_updated_at
  BEFORE UPDATE ON public.reports
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: usage_records
-- =====================================================

CREATE TABLE public.usage_records (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  record_type     public.usage_record_type NOT NULL,
  amount          numeric(12,4) NOT NULL CHECK (amount >= 0),
  unit            text NOT NULL,
  meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_usage_records_org_created ON public.usage_records (organization_id, created_at DESC);
CREATE INDEX idx_usage_records_org_type_created ON public.usage_records (organization_id, record_type, created_at DESC);

-- =====================================================
-- TABLE: tenant_llm_settings
-- =====================================================

CREATE TABLE public.tenant_llm_settings (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id  uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  provider         public.llm_provider NOT NULL DEFAULT 'ollama',
  model            text NOT NULL DEFAULT 'qwen2.5:7b',
  base_url         text,
  api_key_encrypted text,
  temperature      double precision NOT NULL DEFAULT 0.7,
  max_tokens       integer NOT NULL DEFAULT 2048,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_tenant_llm_settings_org UNIQUE (organization_id)
);

CREATE INDEX idx_tenant_llm_settings_org ON public.tenant_llm_settings (organization_id);
CREATE TRIGGER trg_tenant_llm_settings_updated_at
  BEFORE UPDATE ON public.tenant_llm_settings
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================
-- TABLE: insights
-- =====================================================

CREATE TABLE public.insights (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  client_id       uuid NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  model_job_id    uuid NOT NULL REFERENCES public.model_jobs(id) ON DELETE CASCADE,
  type            text NOT NULL CHECK (type IN (
    'channel_performance', 'budget_recommendation', 'anomaly', 'benchmark', 'summary'
  )),
  title           text NOT NULL,
  body            text NOT NULL,
  confidence      double precision NOT NULL DEFAULT 0.0
    CHECK (confidence >= 0 AND confidence <= 1),
  metrics         jsonb NOT NULL DEFAULT '{}'::jsonb,
  source          public.insight_source NOT NULL DEFAULT 'llm',
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_insights_job ON public.insights (model_job_id);
CREATE INDEX idx_insights_client_type ON public.insights (client_id, type);
CREATE INDEX idx_insights_org ON public.insights (organization_id);

-- =====================================================
-- ENABLE ROW-LEVEL SECURITY
-- =====================================================

ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.marketing_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.channel_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.budget_optimizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_llm_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS POLICIES (see Section 4 for full definitions)
-- =====================================================

-- organizations
CREATE POLICY "org_select_members" ON public.organizations FOR SELECT USING (public.is_org_member(id));
CREATE POLICY "org_update_owner" ON public.organizations FOR UPDATE USING (public.is_org_owner(id)) WITH CHECK (public.is_org_owner(id));
CREATE POLICY "org_insert_authenticated" ON public.organizations FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- users
CREATE POLICY "user_select_self" ON public.users FOR SELECT USING (id = auth.uid());
CREATE POLICY "user_update_self" ON public.users FOR UPDATE USING (id = auth.uid()) WITH CHECK (id = auth.uid());
CREATE POLICY "user_insert_own" ON public.users FOR INSERT WITH CHECK (id = auth.uid());

-- memberships
CREATE POLICY "membership_select" ON public.memberships FOR SELECT USING (user_id = auth.uid() OR public.is_org_member(organization_id));
CREATE POLICY "membership_insert_owner" ON public.memberships FOR INSERT WITH CHECK (public.is_org_owner(organization_id));
CREATE POLICY "membership_update_owner" ON public.memberships FOR UPDATE USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));
CREATE POLICY "membership_delete_owner_or_self" ON public.memberships FOR DELETE USING (public.is_org_owner(organization_id) OR user_id = auth.uid());

-- clients
CREATE POLICY "client_select_member" ON public.clients FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "client_insert_analyst" ON public.clients FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "client_update_analyst" ON public.clients FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "client_delete_owner" ON public.clients FOR DELETE USING (public.is_org_owner(organization_id));

-- data_sources
CREATE POLICY "ds_select_member" ON public.data_sources FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "ds_insert_analyst" ON public.data_sources FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "ds_update_analyst" ON public.data_sources FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "ds_delete_analyst" ON public.data_sources FOR DELETE USING (public.is_org_analyst_or_above(organization_id));

-- marketing_data
CREATE POLICY "md_select_member" ON public.marketing_data FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "md_insert_analyst" ON public.marketing_data FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "md_update_analyst" ON public.marketing_data FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "md_delete_owner" ON public.marketing_data FOR DELETE USING (public.is_org_owner(organization_id));

-- model_jobs
CREATE POLICY "mj_select_member" ON public.model_jobs FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "mj_insert_analyst" ON public.model_jobs FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "mj_update_analyst" ON public.model_jobs FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- channel_results
CREATE POLICY "cr_select_member" ON public.channel_results FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "cr_insert_analyst" ON public.channel_results FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- budget_optimizations
CREATE POLICY "bo_select_member" ON public.budget_optimizations FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "bo_insert_analyst" ON public.budget_optimizations FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- reports
CREATE POLICY "report_select_member" ON public.reports FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "report_insert_analyst" ON public.reports FOR INSERT WITH CHECK (public.is_org_analyst_or_above(organization_id));
CREATE POLICY "report_update_analyst" ON public.reports FOR UPDATE USING (public.is_org_analyst_or_above(organization_id)) WITH CHECK (public.is_org_analyst_or_above(organization_id));

-- usage_records
CREATE POLICY "usage_select_owner" ON public.usage_records FOR SELECT USING (public.is_org_owner(organization_id));

-- tenant_llm_settings
CREATE POLICY "llm_select_member" ON public.tenant_llm_settings FOR SELECT USING (public.is_org_member(organization_id));
CREATE POLICY "llm_insert_owner" ON public.tenant_llm_settings FOR INSERT WITH CHECK (public.is_org_owner(organization_id));
CREATE POLICY "llm_update_owner" ON public.tenant_llm_settings FOR UPDATE USING (public.is_org_owner(organization_id)) WITH CHECK (public.is_org_owner(organization_id));
CREATE POLICY "llm_delete_owner" ON public.tenant_llm_settings FOR DELETE USING (public.is_org_owner(organization_id));

-- insights
CREATE POLICY "insight_select_member" ON public.insights FOR SELECT USING (public.is_org_member(organization_id));

-- =====================================================
-- SUPABASE AUTH TRIGGER: auto-create user profile
-- =====================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name'),
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
