-- Fit character snapshots and crawl schedule. Service role writes; anon may read.

create table if not exists public.fit_chars (
  name_key text primary key,
  display_name text not null,
  last_fetched_at timestamptz,
  next_fetch_at timestamptz not null default now(),
  last_level integer,
  last_gold bigint,
  last_played_seconds integer,
  idle_streak integer not null default 0,
  last_etag text,
  payload_hash text,
  created_at timestamptz not null default now()
);

create table if not exists public.fit_snapshots (
  id bigint generated always as identity primary key,
  name_key text not null references public.fit_chars (name_key) on delete cascade,
  fetched_at timestamptz not null default now(),
  source text not null check (source in ('sheet', 'board')),
  level integer,
  gold bigint,
  played_seconds integer,
  body jsonb
);

create index if not exists fit_chars_next_fetch_idx on public.fit_chars (next_fetch_at);
create index if not exists fit_snapshots_name_fetched_idx on public.fit_snapshots (name_key, fetched_at desc);

create table if not exists public.fit_meta (
  key text primary key,
  value jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.fit_chars enable row level security;
alter table public.fit_chars force row level security;
alter table public.fit_snapshots enable row level security;
alter table public.fit_snapshots force row level security;
alter table public.fit_meta enable row level security;
alter table public.fit_meta force row level security;

revoke all on table public.fit_chars from public, anon, authenticated;
revoke all on table public.fit_snapshots from public, anon, authenticated;
revoke all on table public.fit_meta from public, anon, authenticated;

grant select on table public.fit_chars, public.fit_snapshots to anon, authenticated;
