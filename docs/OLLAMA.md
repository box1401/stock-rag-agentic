# Switch the local stack to Ollama

Run agents against a local model — no quota, no API spend, no internet round-trip. Works for Compass Equity in dev mode; production stays on Gemini (Cloud Run can't host a 14B model on free tier with acceptable cold start).

## 1. Install Ollama

Windows / macOS / Linux: <https://ollama.com/download>

```bash
ollama serve              # leaves a daemon at http://localhost:11434
```

## 2. Pull a function-calling-capable model

Compass Equity's AnalystAgent uses tools, so the model **must** support OpenAI-style tool calling. Compatibility table:

| Model | Function calling | Disk | RAM | Speed (CPU only) |
|---|---|---|---|---|
| `qwen2.5:14b` | ✅ excellent | 9 GB | 16 GB | ~12 tok/s |
| `qwen2.5:7b` | ✅ good | 4.7 GB | 8 GB | ~25 tok/s |
| `qwen2.5:3b` | ✅ ok | 2 GB | 4 GB | ~50 tok/s |
| `llama3.1:8b` | ✅ good | 4.7 GB | 8 GB | ~22 tok/s |
| `mistral-nemo` | ✅ good | 7 GB | 12 GB | ~20 tok/s |
| `phi3:mini` | ❌ no tools | 2 GB | 4 GB | fast but useless |

Pull the two used by default:

```bash
ollama pull qwen2.5:14b
ollama pull qwen2.5:7b      # fallback
```

## 3. Switch the stack

```dotenv
# .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL_PRIMARY=qwen2.5:14b
OLLAMA_MODEL_FALLBACK=qwen2.5:7b
```

`host.docker.internal` resolves from the api container to the laptop's host. The `extra_hosts: host-gateway` line in `docker-compose.yml` makes it work on Linux Docker too.

## 4. Restart the api

```bash
docker compose restart api
```

Watch the boot log — should show:

```
api-1  | llm_provider=ollama  base_url=http://host.docker.internal:11434  primary=qwen2.5:14b  fallback=qwen2.5:7b
```

## 5. Smoke test

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker":"2330","mode":"on_demand","language":"en"}' | jq .markdown
```

Expected: same shape of report, ~30-90 seconds latency on CPU (vs ~10-30 s for Gemini Flash). Trace events should show `qwen2.5:14b` instead of `gemini-2.5-flash` in the `model` field.

## 6. Switch back to Gemini

```dotenv
LLM_PROVIDER=gemini
```

```bash
docker compose restart api
```

## What about embedding?

Embedding stays on `gemini-embedding-001` even when `LLM_PROVIDER=ollama`. Reasons:

1. RAGAS-comparable retrieval requires a stable embedding space; switching mid-corpus would invalidate the existing 768-dim vectors in pgvector.
2. The embedding free quota is generous (no per-day cap on embed-content) — quota exhaustion is an LLM-call problem, not an embedding problem.

To fully run offline, swap to Ollama embeddings (`nomic-embed-text` or `bge-m3`). Schema migration required (re-embed all chunks). Out of scope for v1.

## Why Ollama can't be the production LLM (today)

- Cloud Run free tier max RAM 32 GB but each `gemini-2.5-flash` request returns in ~5–10 s; on Cloud Run CPU-only, `qwen2.5:14b` would take 60–120 s. Browser timeout territory.
- Cloud Run scale-to-zero would force the 9 GB model to reload from disk every cold start (1–2 minutes).
- Pinning `min_instances=1` works but burns ~$15/month per service to keep the model warm — defeats the free-tier story.

If a future production target needs offline LLM, the path is a dedicated GPU box (Hetzner, RunPod) running Ollama and a private VPN connector to Cloud Run. Not in scope for this portfolio.
