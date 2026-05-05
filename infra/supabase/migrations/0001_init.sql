create extension if not exists vector;
create extension if not exists pg_trgm;

create table if not exists tickers (
  symbol text primary key,
  name text not null,
  market text not null check (market in ('TWSE', 'TPEX', 'OTHER')),
  industry text,
  created_at timestamptz not null default now()
);

create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  ticker text not null references tickers(symbol),
  mode text not null check (mode in ('daily', 'weekly', 'on_demand')),
  markdown text not null,
  pdf_url text,
  agent_trace jsonb,
  citations jsonb,
  created_at timestamptz not null default now()
);
create index if not exists reports_ticker_idx on reports(ticker, created_at desc);
create index if not exists reports_user_idx on reports(user_id, created_at desc);

create table if not exists signals (
  id uuid primary key default gen_random_uuid(),
  ticker text not null references tickers(symbol),
  report_id uuid references reports(id) on delete cascade,
  signal_date date not null,
  close numeric,
  ma5 numeric,
  ma20 numeric,
  ma60 numeric,
  rsi numeric,
  bias_20 numeric,
  pe numeric,
  pe_percentile numeric,
  recommendation text,
  payload jsonb,
  created_at timestamptz not null default now(),
  unique (ticker, signal_date)
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  source_type text not null check (source_type in ('news', 'filing', 'transcript', 'thesis', 'web')),
  source_url text,
  ticker text references tickers(symbol),
  title text,
  published_at timestamptz,
  raw_path text,
  created_at timestamptz not null default now()
);
create index if not exists documents_ticker_idx on documents(ticker, published_at desc);

create table if not exists chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  embedding vector(768),
  tsv tsvector generated always as (to_tsvector('simple', content)) stored,
  metadata jsonb,
  unique (document_id, chunk_index)
);
create index if not exists chunks_embedding_idx on chunks using hnsw (embedding vector_cosine_ops);
create index if not exists chunks_tsv_idx on chunks using gin(tsv);

create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  ticker text references tickers(symbol),
  title text,
  created_at timestamptz not null default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system', 'tool')),
  content text not null,
  citations jsonb,
  created_at timestamptz not null default now()
);
create index if not exists messages_conv_idx on messages(conversation_id, created_at);

insert into tickers(symbol, name, market, industry) values
  ('2330', 'TSMC',                 'TWSE', 'Semiconductors'),
  ('2454', 'MediaTek',             'TWSE', 'Semiconductors'),
  ('2317', 'Hon Hai Precision',    'TWSE', 'Electronics Manufacturing'),
  ('0050', 'Yuanta Taiwan 50 ETF', 'TWSE', 'ETF'),
  ('3711', 'ASE Technology',       'TWSE', 'Semiconductors'),
  ('2308', 'Delta Electronics',    'TWSE', 'Electronic Components')
on conflict (symbol) do nothing;
