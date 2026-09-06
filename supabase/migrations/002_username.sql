-- Username on public.users. Apply after 001.
-- Paste in the SQL editor.

alter table public.users
  add column if not exists username text;

update public.users
set username = 'user_' || substr(replace(id::text, '-', ''), 1, 8)
where username is null or btrim(username) = '';

with dups as (
  select id, username, row_number() over (partition by lower(username) order by created_at) as n
  from public.users
)
update public.users u
set username = u.username || '_' || d.n
from dups d
where u.id = d.id and d.n > 1;

alter table public.users
  alter column username set not null;

create unique index if not exists users_username_lower_idx
  on public.users (lower(username));

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  chosen text;
begin
  chosen := nullif(btrim(new.raw_user_meta_data ->> 'username'), '');
  if chosen is null then
    raise exception 'username required';
  end if;
  insert into public.users (id, username, display_name)
  values (new.id, chosen, chosen)
  on conflict (id) do update
    set username = excluded.username,
        display_name = excluded.display_name;
  return new;
end;
$$;

revoke all on function public.handle_new_user() from public, anon, authenticated;

create index if not exists page_revisions_created_idx
  on public.page_revisions (created_at desc);
