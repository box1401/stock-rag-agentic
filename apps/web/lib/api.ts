export interface AnalyzeRequest {
  ticker: string;
  mode?: "daily" | "weekly" | "on_demand";
  language?: "zh-TW" | "en";
}

export interface TraceEvent {
  timestamp: string;
  agent: "supervisor" | "data" | "analyst" | "risk" | "reporter";
  event: string;
  detail?: Record<string, unknown> | null;
}

export interface AnalyzeResponse {
  ticker: string;
  mode: string;
  language: string;
  markdown: string;
  citations: Array<Record<string, unknown>>;
  indicators: Record<string, unknown> | null;
  trace: TraceEvent[];
  generated_at: string;
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const resp = await fetch(`${BASE}/api/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: "zh-TW", mode: "on_demand", ...req }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${resp.status}: ${text}`);
  }
  return (await resp.json()) as AnalyzeResponse;
}

export interface TickerRow {
  symbol: string;
  name: string;
  market: string;
  industry: string | null;
}

export async function listTickers(): Promise<TickerRow[]> {
  const resp = await fetch(`${BASE}/api/v1/tickers`, { cache: "no-store" });
  if (!resp.ok) return [];
  return (await resp.json()) as TickerRow[];
}
