-- KarlAI retrieval. Paste in the SQL editor after vector is enabled.
-- Dashboard: Database → Extensions → vector
-- Then: node scripts/embed_wiki_and_gc.mjs
--
-- Service role only. Anon/authenticated must not read chunks or embeddings.

create extension if not exists vector;

create table if not exists public.wiki_chunks (
  id bigint generated always as identity primary key,
  source text not null check (source in ('wiki', 'game')),
  ref text not null,
  path text not null default '',
  title text not null,
  chunk_i int not null default 0,
  text text not null,
  embedding vector(1536) not null,
  unique (source, ref, chunk_i)
);

create index if not exists wiki_chunks_source_idx on public.wiki_chunks (source);
create index if not exists wiki_chunks_embedding_hnsw
  on public.wiki_chunks
  using hnsw (embedding vector_cosine_ops);

create or replace function public.match_chunks(
  query_embedding vector(1536),
  match_count int default 8,
  source_filter text default null
)
returns table (
  id bigint,
  source text,
  path text,
  title text,
  text text,
  distance float
)
language sql
stable
set search_path = public
as $$
  select
    c.id,
    c.source,
    c.path,
    c.title,
    c.text,
    (c.embedding <=> query_embedding)::float as distance
  from public.wiki_chunks c
  where source_filter is null or c.source = source_filter
  order by c.embedding <=> query_embedding
  limit least(greatest(coalesce(match_count, 8), 1), 24);
$$;

alter table public.wiki_chunks enable row level security;

revoke all on table public.wiki_chunks from public, anon, authenticated;
revoke all on function public.match_chunks(vector, int, text) from public, anon, authenticated;
