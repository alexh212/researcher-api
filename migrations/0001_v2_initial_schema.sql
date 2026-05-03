create extension if not exists pgcrypto;

-- Users (mirrors Supabase auth.users via id)
create table users (
  id uuid primary key,
  email text not null unique,
  display_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  trial_reports_limit integer not null default 2,
  daily_runs_limit integer not null default 5,
  stripe_customer_id text,
  subscription_status text,
  plan_tier text,
  trial_ends_at timestamptz
);

-- Projects (workspaces)
create table projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references users(id) on delete cascade,
  name text not null,
  category text,
  metadata jsonb not null default '{}',
  current_report_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index idx_projects_owner on projects(owner_id);

-- Reports (immutable versioned snapshots)
create table reports (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  version integer not null,
  parent_report_id uuid references reports(id) on delete set null,
  body_markdown text not null,
  agent_config_snapshot jsonb not null,
  created_at timestamptz not null default now(),
  unique (project_id, version)
);
create index idx_reports_project on reports(project_id, version desc);

alter table projects
  add constraint fk_projects_current_report
  foreign key (current_report_id) references reports(id) on delete set null;

-- AgentRuns (execution traces, one per Report)
create table agent_runs (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references reports(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  status text not null check (status in ('running','completed','failed','killed_cost_cap')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  planner_output jsonb,
  researcher_traces jsonb,
  evaluator_scores jsonb,
  total_cost_cents integer,
  error text
);

create unique index idx_agent_runs_one_in_flight
  on agent_runs(user_id) where status = 'running';
create index idx_agent_runs_user_started on agent_runs(user_id, started_at desc);

-- Sources (content-addressed snapshots)
create table sources (
  id uuid primary key default gen_random_uuid(),
  url text not null,
  content_snapshot text not null,
  fetched_at timestamptz not null default now(),
  added_by_user_id uuid references users(id) on delete set null
);
create index idx_sources_url on sources(url);

-- SourceUsage (which sources informed which reports)
create table source_usage (
  report_id uuid not null references reports(id) on delete cascade,
  source_id uuid not null references sources(id) on delete cascade,
  role text not null,
  primary key (report_id, source_id)
);
create index idx_source_usage_source on source_usage(source_id);

-- Notes (mutable user annotations)
create table notes (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  body text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index idx_notes_project on notes(project_id, created_at desc);

-- ShareLinks (polymorphic via two nullable FKs + CHECK)
create table share_links (
  id uuid primary key default gen_random_uuid(),
  target_type text not null check (
    target_type in ('report','project_snapshot','project_live')
  ),
  report_id uuid references reports(id) on delete cascade,
  project_id uuid references projects(id) on delete cascade,
  token text not null unique,
  created_by uuid not null references users(id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  revoked_at timestamptz,
  password_hash text,
  requires_auth boolean not null default false,
  view_count integer not null default 0,
  check (
    (report_id is not null)::int + (project_id is not null)::int = 1
  )
);
create index idx_share_links_token on share_links(token);

-- Events (analytics + usage source-of-truth)
create table events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  project_id uuid references projects(id) on delete set null,
  session_id text,
  event_type text not null,
  properties jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create index idx_events_user_created on events(user_id, created_at desc);
create index idx_events_type_created on events(event_type, created_at desc);

-- Waitlist (pricing-preference signal from trial-cap users)
create table waitlist (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  email text not null,
  pricing_preference text,
  message text,
  created_at timestamptz not null default now()
);
