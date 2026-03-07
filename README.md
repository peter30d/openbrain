# OpenBrain Gateway

Canonical memory service for:

- OpenClaw runtime
- local hybrid memory (Postgres + pgvector + Markdown archive)
- Brian Madden upstream knowledge federation

## Run

1. Create Postgres DB and enable pgvector
2. Apply `sql/001_init.sql`
3. Copy `.env.example` to `.env`
4. Install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

5. Start:

```bash
uvicorn openbrain.api:app --host 127.0.0.1 --port 8094
```

## CLI

```bash
openbrainctl capture "Peter prefers concise technical explanations."
openbrainctl search "What does Peter prefer?"
openbrainctl federated "How should AI change knowledge work?"
```

