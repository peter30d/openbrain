CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_records (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    cleaned_text TEXT NOT NULL,
    summary TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    source_surface TEXT NOT NULL,
    source_session_id TEXT,
    project TEXT,
    people JSONB NOT NULL DEFAULT '[]'::jsonb,
    topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    action_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    importance INTEGER NOT NULL DEFAULT 3,
    sensitivity TEXT NOT NULL DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'active',
    provenance_type TEXT NOT NULL DEFAULT 'local',
    provenance_ref TEXT,
    archive_path TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding VECTOR(384)
);

CREATE INDEX IF NOT EXISTS idx_memory_records_captured_at
ON memory_records (captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_records_memory_type
ON memory_records (memory_type);

CREATE INDEX IF NOT EXISTS idx_memory_records_project
ON memory_records (project);

CREATE INDEX IF NOT EXISTS idx_memory_records_status
ON memory_records (status);

CREATE INDEX IF NOT EXISTS idx_memory_records_embedding
ON memory_records USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE TABLE IF NOT EXISTS external_promotions (
    id UUID PRIMARY KEY,
    local_memory_id UUID NOT NULL REFERENCES memory_records(id) ON DELETE CASCADE,
    external_source TEXT NOT NULL,
    external_title TEXT NOT NULL,
    external_uri TEXT,
    external_excerpt TEXT,
    promotion_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gateway_audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

