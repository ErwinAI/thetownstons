-- Fit OG cards in storage. Service role writes; public may read the bucket.

alter table public.fit_chars
  add column if not exists og_hash text,
  add column if not exists og_path text,
  add column if not exists og_at timestamptz;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('fit-og', 'fit-og', true, 2097152, array['image/png'])
on conflict (id) do update
  set public = true,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists fit_og_public_read on storage.objects;
create policy fit_og_public_read
  on storage.objects
  for select
  to public
  using (bucket_id = 'fit-og');
