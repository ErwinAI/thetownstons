-- Image approval queue + site settings. Apply after 002.

create table if not exists public.site_settings (
  key text primary key,
  value jsonb not null
);

insert into public.site_settings (key, value)
values ('open_edits', 'false'::jsonb)
on conflict (key) do nothing;

create table if not exists public.wiki_images (
  id uuid primary key default gen_random_uuid(),
  storage_path text not null,
  mime text not null,
  original_name text,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  uploaded_by uuid references public.users (id),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by uuid references public.users (id)
);

create index if not exists wiki_images_status_idx on public.wiki_images (status, created_at desc);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'wiki',
  'wiki',
  false,
  2097152,
  array['image/jpeg', 'image/png', 'image/gif', 'image/webp']
)
on conflict (id) do nothing;

alter table public.site_settings enable row level security;
alter table public.site_settings force row level security;
alter table public.wiki_images enable row level security;
alter table public.wiki_images force row level security;

drop policy if exists settings_read on public.site_settings;
create policy settings_read on public.site_settings
  for select to anon, authenticated
  using (true);

drop policy if exists images_read on public.wiki_images;
create policy images_read on public.wiki_images
  for select to anon, authenticated
  using (true);

revoke all on table public.site_settings from public, anon, authenticated;
revoke all on table public.wiki_images from public, anon, authenticated;
grant select on table public.site_settings, public.wiki_images to anon, authenticated;
