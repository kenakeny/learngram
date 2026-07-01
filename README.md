# learngram

Productive doom-scrolling — a Twitter-like infinite feed of system-design knowledge, where every "go deeper" drops you into a traversal of a knowledge graph.

## Quickstart (PowerShell)

### 1. Start Postgres

```powershell
docker compose -f db/docker-compose.yml up -d
```

### 2. Copy env and configure

```powershell
Copy-Item .env.example .env
# Edit .env — at minimum set DATABASE_URL (default works with Docker Compose above)
```

### 3. Install Python dependencies and run migrations

```powershell
uv sync
uv run migrate
uv run seed
```

Verify:
```powershell
docker exec -it learngram-db psql -U learngram -d learngram -c "SELECT count(*) FROM nodes; SELECT count(*) FROM edges;"
```

Expected: nodes ≥ 35, edges ≥ 40.

### 4. Start the API

```powershell
uv run --package learngram-api uvicorn learngram_api.main:app --reload --port 8000
```

Check: http://localhost:8000/health → `{"status":"ok","db":true}`
Feed: http://localhost:8000/feed → 20 card-shaped seed nodes

### 5. Start the web app

```powershell
npm --prefix apps/web install
npm --prefix apps/web run dev
```

Open http://localhost:3000 — scroll-snap feed of system-design concept cards.

---

## Project structure

```
learngram/
├── apps/web/          # Next.js 15 + Tailwind + shadcn/ui
├── services/
│   ├── shared/        # psycopg3 pool, migration runner, LLM + embedding adapters
│   └── api/           # FastAPI: /health, /feed
├── db/
│   ├── docker-compose.yml
│   ├── migrations/    # forward-only SQL migrations
│   └── seed/          # hand-seeded nodes + edges
├── pyproject.toml     # uv workspace root
└── .env.example
```

## Phases

| Phase | Status | Goal |
|-------|--------|------|
| 1 — Foundation | ✅ | Schema · seed nodes · FastAPI feed · Next.js scroll feed |
| 2 — Ingestion | 🔜 | Scrape primer + blogs · LLM proposes graph extensions · human approval CLI |
| 3 — Card generation | 🔜 | RAG-grounded cards per node · scoring · review tool |
| 4 — Feed + rabbit hole | 🔜 | Ranked walk · go-deeper traversal · search · topic picker |
| 5 — Taste iteration | 🔜 | Prompt tuning · corpus expansion · personalization signals |

## Content pipeline (Phases 2–3)

Run from the repo root, in order. Uses `LLM_PROVIDER` / `EMBEDDING_PROVIDER` from `.env`.

```powershell
uv run ingest-primer          # scrape System Design Primer → documents
uv run ingest-blogs           # scrape engineering blog RSS → documents
uv run extract                # LLM proposes new nodes/edges from documents
uv run review                 # human-approve proposals into the graph
uv run embed                  # embed nodes + chunk/embed documents (required for RAG)
uv run generate               # RAG-grounded cards per node → cards table
```

`embed` populates `nodes.embedding` and the `document_chunks` table. `generate`
then retrieves the nearest source chunks per node, injects them as grounding
facts into the prompt, and records their document ids on each card
(`cards.source_doc_ids`). Skipping `embed` still works but produces ungrounded
cards (the generator falls back to concept description only).

## Ingest your own files (one shot)

Drop a Markdown or PDF and it runs the whole chain automatically — convert →
extract concepts → build the graph (no manual review) → embed → generate cards.

**CLI:**
```powershell
uv run ingest-file path\to\notes.pdf        # one file
uv run ingest-file path\to\folder           # every supported file in a folder
uv run ingest-file notes.pdf --land-only    # insert documents only, skip the pipeline
```
Supported: `.md .markdown .txt .pdf .docx .pptx .html`. Non-Markdown files are
converted with [markitdown](https://github.com/microsoft/markitdown).

**Frontend:** open the **Ingest** page (nav rail), drop a file, and watch the
progress (convert → extract → graph → embed → cards). The API processes it as a
background job (`POST /ingest`, poll `GET /ingest/{id}`) so long LLM runs don't
block the request. New cards appear in the Home feed when it finishes.

> Topics are AI-judged: the extractor reuses an existing topic when a concept fits
> or coins a new one, so the topic set grows with what you ingest.

## LLM / embedding providers

Set `LLM_PROVIDER` and `EMBEDDING_PROVIDER` in `.env` to `gemini` or `ollama`.

- **Gemini:** set `GEMINI_API_KEY`; models default to `gemini-2.5-pro` / `text-embedding-004`.
- **Ollama:** run Ollama locally with `qwen2.5` and `nomic-embed-text` pulled. Set `OLLAMA_BASE_URL` if not on default port.

Phase 1 makes zero LLM calls — no key required.
