-- Title + body full-text search. Title ranks highest.

create or replace function public.wiki_plain_text(html text, md text)
returns text
language sql
immutable
as $$
  select regexp_replace(
    regexp_replace(
      coalesce(nullif(btrim(coalesce(md, '')), ''), coalesce(html, '')),
      '<[^>]+>',
      ' ',
      'g'
    ),
    '\s+',
    ' ',
    'g'
  );
$$;

alter table public.pages
  add column if not exists search_tsv tsvector
  generated always as (
    setweight(to_tsvector('english', coalesce(title, '')), 'A')
    || setweight(to_tsvector('english', coalesce(description, '')), 'B')
    || setweight(to_tsvector('english', public.wiki_plain_text(html, body_md)), 'C')
  ) stored;

drop index if exists public.pages_search_idx;
create index pages_search_idx on public.pages using gin (search_tsv);

create or replace function public.search_wiki(q text, max_rows int default 50)
returns table (title text, path text, rank real, headline text)
language sql
stable
security invoker
set search_path = public
as $$
  with query as (
    select websearch_to_tsquery('english', btrim(coalesce(q, ''))) as tsq
  )
  select
    p.title,
    p.path,
    ts_rank_cd(p.search_tsv, query.tsq) as rank,
    ts_headline(
      'english',
      left(public.wiki_plain_text(p.html, p.body_md), 2000),
      query.tsq,
      'MaxWords=24, MinWords=12, StartSel=<b>, StopSel=</b>'
    ) as headline
  from public.pages p, query
  where length(btrim(coalesce(q, ''))) >= 2
    and query.tsq is not null
    and p.search_tsv @@ query.tsq
  order by rank desc, p.title
  limit greatest(1, least(coalesce(max_rows, 50), 100));
$$;

revoke all on function public.search_wiki(text, int) from public;
grant execute on function public.search_wiki(text, int) to anon, authenticated;
grant execute on function public.wiki_plain_text(text, text) to anon, authenticated;
