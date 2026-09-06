-- Townstons wiki store. Paste in the SQL editor, then:
-- node scripts/import_wiki_to_supabase.mjs
--
-- Access model:
--   anon:          read pages, aliases, revisions, public profiles
--   authenticated: edit unlocked pages, insert revisions, edit own profile
--   admin:         edit locked pages (set role in SQL: update users set role = 'admin' where id = '...')
--   no deletes
--   aliases: service role only (import)
-- Writes from the Nuxt API use the secret key after verifying a user JWT.

create table if not exists public.users (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  avatar_url text,
  prefs jsonb not null default '{}'::jsonb,
  role text not null default 'editor' check (role in ('editor', 'admin')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, display_name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1))
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

revoke all on function public.handle_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

create table if not exists public.pages (
  slug text primary key,
  fold_key text not null unique,
  title text not null,
  wiki_title text not null,
  path text not null unique,
  description text,
  html text not null default '',
  body_md text,
  -- Membership only. Category pages list members/subcats from this array.
  -- Never store member link dumps in html. Subcat = a Category/* page whose
  -- categories[] includes the parent name.
  categories text[] not null default '{}',
  images text[] not null default '{}',
  locked boolean not null default false,
  updated_at timestamptz not null default now(),
  updated_by uuid references public.users (id)
);

create index if not exists pages_fold_key_idx on public.pages (fold_key);
create index if not exists pages_categories_idx on public.pages using gin (categories);
create index if not exists pages_search_idx on public.pages
  using gin (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')));

create table if not exists public.page_aliases (
  alias text primary key,
  slug text not null references public.pages (slug) on delete cascade
);

create table if not exists public.page_revisions (
  id bigint generated always as identity primary key,
  slug text not null references public.pages (slug) on delete cascade,
  title text not null,
  html text not null,
  body_md text,
  editor text,
  editor_id uuid references public.users (id),
  created_at timestamptz not null default now()
);

create index if not exists page_revisions_slug_idx on public.page_revisions (slug, created_at desc);

create or replace function public.random_page_path()
returns text
language sql
stable
security invoker
set search_path = public
as $$
  select path
  from public.pages
  where slug not ilike 'Category/%'
    and slug not ilike 'Category:%'
  order by random()
  limit 1;
$$;

create or replace function public.category_lists(cat text)
returns table (kind text, title text, path text)
language sql
stable
security invoker
set search_path = public
as $$
  with want as (
    select lower(replace(trim(cat), '_', ' ')) as key
  )
  select
    case
      when p.slug ilike 'Category/%' or p.slug ilike 'Category:%'
        or p.wiki_title ilike 'Category:%' or p.path ilike '/wiki/Category/%'
        then 'subcat'
      else 'member'
    end as kind,
    p.title,
    p.path
  from public.pages p, want
  where exists (
    select 1
    from unnest(p.categories) as c
    where lower(replace(c, '_', ' ')) = want.key
  );
$$;

create or replace function public.is_admin()
returns boolean
language sql
stable
security invoker
set search_path = public
as $$
  select exists (
    select 1 from public.users
    where id = auth.uid() and role = 'admin'
  );
$$;

revoke all on function public.random_page_path() from public;
revoke all on function public.category_lists(text) from public;
revoke all on function public.is_admin() from public;
grant execute on function public.random_page_path() to anon, authenticated;
grant execute on function public.category_lists(text) to anon, authenticated;
grant execute on function public.is_admin() to authenticated;

alter table public.users enable row level security;
alter table public.users force row level security;
alter table public.pages enable row level security;
alter table public.pages force row level security;
alter table public.page_aliases enable row level security;
alter table public.page_aliases force row level security;
alter table public.page_revisions enable row level security;
alter table public.page_revisions force row level security;

drop policy if exists users_read on public.users;
create policy users_read on public.users
  for select to anon, authenticated
  using (true);

drop policy if exists users_update_self on public.users;
create policy users_update_self on public.users
  for update to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

drop policy if exists pages_read on public.pages;
create policy pages_read on public.pages
  for select to anon, authenticated
  using (true);

drop policy if exists pages_insert on public.pages;
create policy pages_insert on public.pages
  for insert to authenticated
  with check (true);

drop policy if exists pages_update on public.pages;
create policy pages_update on public.pages
  for update to authenticated
  using (not locked or public.is_admin())
  with check (not locked or public.is_admin());

drop policy if exists aliases_read on public.page_aliases;
create policy aliases_read on public.page_aliases
  for select to anon, authenticated
  using (true);

drop policy if exists revisions_read on public.page_revisions;
create policy revisions_read on public.page_revisions
  for select to anon, authenticated
  using (true);

drop policy if exists revisions_insert on public.page_revisions;
create policy revisions_insert on public.page_revisions
  for insert to authenticated
  with check (true);

revoke all on table public.users from public, anon, authenticated;
revoke all on table public.pages from public, anon, authenticated;
revoke all on table public.page_aliases from public, anon, authenticated;
revoke all on table public.page_revisions from public, anon, authenticated;

grant select on table public.users, public.pages, public.page_aliases, public.page_revisions to anon, authenticated;
grant update (display_name, avatar_url, prefs, updated_at) on table public.users to authenticated;
grant insert, update on table public.pages to authenticated;
grant insert on table public.page_revisions to authenticated;
grant usage, select on all sequences in schema public to authenticated;
