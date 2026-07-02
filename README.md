# learngram

"Productive" Doom-scrolling but it actually teaches you something.  It's a Twitter-style feed of technical , sooo think 
analogies, memes, and in-character posts from a few fake accounts. All of them are generated from real docs/sources so the content isnt just generic AI slop

You feed it documents (scrape them or upload your own), an LLM pulls the concepts out into a knowledge graph, and then it writes feed cards for each concept. Everything gets grounded in the source material and fact checked before it shows up in the feed.

## Architecture

- `apps/web` : the Next.js frontend 
- `services/api` : FastAPI backend, serves the feed and handles ingestion/feedback
- `services/ingestion` : all the pipeline jobs (scrape, extract, embed, generate)
- `services/shared` : db pool, migrations, and the LLM/embedding adapters (Gemini or Ollama)
- `db` : Postgres + pgvector, migrations and the starter seed graph

## Running it 

Start the db:
```powershell
docker compose -f db/docker-compose.yml up -d
```

Set up your env:
```md
Rename .env.example to .env
```

Install and migrate:
```powershell
uv sync
uv run migrate
uv run seed
```

Start the API:
```powershell
uv run --package learngram-api uvicorn learngram_api.main:app --reload --port 8000
```
Should be up at http://localhost:8000/

Start the frontend:
```powershell
npm --prefix apps/web install
npm --prefix apps/web run dev
```
Open http://localhost:3000.

Right after seeding the feed is basically empty because there are no generated cards yet, as the version on github is without data yet. Run the pipeline below to fill it.

## The content pipeline

Run these from the repo root, in order:

```powershell
uv run ingest-primer      # scrape the System Design Primer into documents
uv run ingest-blogs       # scrape some engineering blogs
uv run extract            # LLM reads the docs and proposes graph nodes/edges
uv run review             # approve the proposals into the graph (manual)
uv run embed              # embed the nodes + chunk and embed the docs
uv run generate           # write RAG-grounded cards for each node
uv run generate-posts     # write the persona posts for each node
```

Some flags you'll want: `--limit N` on generate to only do a few, `--regen` to redo nodes that already have cards, `--rechunk` on embed to rebuild all the document chunks 

## How the RAG part works

For each node, generate embeds a query and pulls the closest document chunks by cosine distance (`retrieval.py`, the distance cutoff is tuned to the embedding model). Those chunks go into the prompt as facts the model has to stick to, and their doc ids get saved on the card.

Then before the card is saved, another LLM call judges how well it matches those facts and writes a `quality_score` (0 to 1). A few rules fall out of that:

- no grounding found : no card.
- score below 0.6 : thrown away
- the feed only shows cards at 0.6 or higher, so bad or old cards just stay hidden instead of getting deleted

If you swap the embedding model or change the chunker, rerun `embed --rechunk` and re-check the distance cutoff (there's a note in `retrieval.py` on how).

## The personas

`generate-posts` makes one post per concept from each fake account, each with their own voice:

- **Marcus** (`@exhausted-senior`) : burnt out staff engineer, does rants
- **Aria** (`@10x-engineer`) : just says the answer bluntly, yes they're like that
- **Sam** (`@friendly-junior`) : stackoverflow style answer
- **Devon** (`@chatgpt-intern`) : meme posts, "i asked ChatGPT what X is and it said:"

 ### Note

Devon's is posting a *wrong* answer, so the correct answer is in the same post right under the joke, and the fact-checker grades the correction not the joke. Nothing wrong makes it into the feed without a fix attached.

## Feedback loop

There's a RLHF loop here we can do, essentially you can thumbs up/down cards in the feed. That gets saved, and then:

```powershell
uv run tune-analogies      # takes the feedback and rewrites the analogy voice prompt
uv run tune-analogies --dry-run   # see what it'd change without writing
```

It distills the up/down votes into style notes and appends them to `prompts/analogy_system.md`, so the next `generate` run writes in a better voice tuned SPECIFICALLY FOR YOUUU. Rate then tune then regenerate.

## Uploading your own files

Drop a file and it runs the whole chain automatically (convert then extract then build graph then embed then generate), no manual review step:

```powershell
uv run ingest-file path\to\notes.pdf     # one file
uv run ingest-file path\to\folder        # a whole folder
uv run ingest-file notes.pdf --land-only # just save the docs, skip the pipeline
```

Works with `.md .txt .pdf .docx .pptx .html`. Non-markdown gets converted with markitdown.

Or just use the **Ingest** page in the web app where you drop a file and watch the progress bar. The API runs it as a background job so it doesn't block, and the new cards show up in the feed when it's done.

## Providers

Set `LLM_PROVIDER` and `EMBEDDING_PROVIDER` in `.env` : either `gemini` or `ollama`, and they can be different (e.g. generate locally, embed with Gemini).

**Gemini:** set `GEMINI_API_KEY`. Free tier is ~10 requests/min so keep `LLM_RPM` in line with that or you'll get rate limited.

**Ollama:** run it locally, pull a generation model and `nomic-embed-text` for embeddings. The adapter adds nomic's `search_document:`/`search_query:` prefixes for you. Turn `LLM_RPM` way up since there's no quota locally, otherwise the rate limiter just slows you down for no reason.

## The API

- `GET /health` : is it alive + can it reach the db
- `GET /feed` : the feed, filtered by quality. takes `?topic=`, `?persona=`, `?limit=`
- `GET /topics` : topics with counts
- `GET /personas` : the accounts with post counts
- `GET /graph` : nodes + edges for the graph page
- `POST /ingest` / `GET /ingest/{id}` : upload a file, then poll the job
- `POST /feedback` : save a 👍/👎 on a card

## Status

Working: the schema + seed graph, scraping and file upload, LLM extraction into the graph, RAG card generation with the fact-check gate, the personas, and the feedback tuning loop.

Not done yet: the "rabbit hole" , clicking go-deeper on a card to walk the graph, ranking the feed properly, and search.
