-- Search counts for Fit character lookups. Service role writes; anon may read.

alter table public.fit_chars
  add column if not exists search_count integer not null default 0,
  add column if not exists last_searched_at timestamptz;

create table if not exists public.fit_search_log (
  id bigint generated always as identity primary key,
  name_key text not null,
  display_name text not null,
  searched_at timestamptz not null default now()
);

create index if not exists fit_search_log_searched_idx on public.fit_search_log (searched_at desc);
create index if not exists fit_chars_search_count_idx on public.fit_chars (search_count desc);

alter table public.fit_search_log enable row level security;
alter table public.fit_search_log force row level security;
revoke all on table public.fit_search_log from public, anon, authenticated;
grant select on table public.fit_search_log to anon, authenticated;

create or replace function public.record_fit_search(p_name_key text, p_display_name text)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.fit_chars (name_key, display_name, search_count, last_searched_at)
  values (p_name_key, p_display_name, 1, now())
  on conflict (name_key) do update
    set search_count = public.fit_chars.search_count + 1,
        last_searched_at = now(),
        display_name = excluded.display_name;
  insert into public.fit_search_log (name_key, display_name)
  values (p_name_key, p_display_name);
end;
$$;

revoke all on function public.record_fit_search(text, text) from public, anon, authenticated;
grant execute on function public.record_fit_search(text, text) to service_role;
