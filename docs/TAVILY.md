# Hooking up Tavily for live news search

Tavily is the cleanest news-search API for LLM agents — it returns clean article snippets with publication dates and source domains. Free tier: 1000 searches / month, no credit card.

## 1. Get the key

1. Open <https://app.tavily.com/sign-in> and sign in (Google OAuth works).
2. **Settings → API Keys → Create New API Key** with name "compass-equity".
3. Copy the key (starts with `tvly-...`). Save it; the dashboard hides it after first reveal.

## 2. Put it into `.env.production` and seed Secret Manager

```bash
echo "TAVILY_API_KEY=tvly-..." >> .env.production
./infra/scripts/seed-secrets.sh compass-equity
```

## 3. Force a new Cloud Run revision so api picks up the new value

```bash
gcloud run services update compass-api \
  --project=compass-equity --region=asia-east1 \
  --update-env-vars=COMPASS_REFRESH=$(date +%s)
```

## 4. Verify

```bash
API=https://compass-api-aujzogkiva-de.a.run.app
curl -X POST "$API/api/v1/analyze" -H "Content-Type: application/json" \
  -d '{"ticker":"2330","mode":"on_demand","language":"en"}' | jq '.trace[] | select(.event=="tool:news_search")'
```

Expected: the trace shows `tool:news_search` with `result_chars` >> 0 (was `(0 results — no API key)` before). The final markdown includes references to recent news headlines.

## How the api uses it

`app/tools/news.py:tavily_search()` is called via Gemini function calling when the AnalystAgent decides recent news matters for the question. With no key configured, the function returns an empty list and the agent gracefully reports "no recent news available" — no crash, no fabricated content.

## Cost notes

- Free tier resets monthly; check usage at <https://app.tavily.com/usage>.
- A typical `/analyze` run uses 0–1 Tavily searches. 1000 / month = ~30/day, plenty for a portfolio demo.
- If you hit the limit, the agent transparently degrades to using only RAG + market data.
