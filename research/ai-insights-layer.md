# AI / LLM Insights Layer

*Research date: 2026-08-01. Based on deep-research workflow (5 agents).*

## Provider Recommendation

**Thin `typing.Protocol` + two concrete implementations.**

- `OpenAIProvider`: one class serves BOTH OpenAI and Ollama via `openai` SDK with `base_url`. Ollama exposes an OpenAI-compatible endpoint at `http://localhost:11434/v1`.
- `AnthropicProvider`: native `anthropic` SDK ONLY — Anthropic's OpenAI-compat endpoint IGNORES `response_format`, so structured JSON would silently break for Claude tenants.
- **Reject** LiteLLM (12 transitive deps, unneeded breadth for 3 providers), LangChain (version-coordination overhead), Vercel AI SDK (TS-first, Python port beta).
- Adopt LiteLLM later only if you need proxy/spend-tracking/100+ providers.

## Interface (protocol)

```python
class LLMProvider(Protocol):
    async def complete(self, req: ChatRequest) -> ChatResponse: ...
    async def stream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]: ...
    async def extract(self, req: ChatRequest, schema: type[BaseModel]) -> BaseModel: ...
```

- pydantic at every boundary; never trust raw LLM output — re-validate with `model_validate`.
- Structured output: OpenAI/Ollama `response_format={type:json_schema,...}`; Anthropic native `messages.create` with json_schema.
- Per-tenant override: `tenant_llm_settings(org_id, provider, model, base_url, api_key_ref)`. api_key_ref is a secret reference, never raw key.
- Streaming: SSE via FastAPI `StreamingResponse`; for structured output, stream deltas, reassemble, validate server-side.

## Ollama Model Selection (deep-research findings)

### Default (budget): Qwen2.5-7B-Instruct
- Explicitly trained for reliable structured JSON + table understanding (exactly MMM insight output)
- 128K context, up to 8K output tokens, native tool calling, Apache 2.0, 29+ languages
- ~5GB VRAM at Q4_K_M -> fits RTX 3090/4090 with room for KV cache + 2-3 parallel requests
- Serve: `format=<full JSON schema>` (schema-mode, not just `format:'json'`), temperature 0-0.1, `num_ctx` 8192-16384
- Ultra-tight budget fallback: Qwen3-4B (2.5GB)

### Premium: Qwen2.5-32B-Instruct
- Same structured-output training as 7B, much better reasoning/prose
- ~19-20GB at Q4_K_M -> fits RTX 4090 (24GB) with `OLLAMA_KV_CACHE_TYPE=q4_0`, num_ctx 4096-8192
- Throughput-first alternative: Qwen2.5-14B (Q5_K_M ~11GB, 2-4 parallel)
- JSON-reliability-first alternative: Mistral Small 24B (Q4_K_M ~14GB, competitive with GPT-4o-mini)

### Production serving tips
- `OLLAMA_HOST=0.0.0.0:11434`, `OLLAMA_KV_CACHE_TYPE=q4_0`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_NUM_PARALLEL=2-3`, `OLLAMA_CONTEXT_LENGTH=8192`, `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=-1` (preload both tiers)
- Ollama has NO built-in rate limiting -> put behind nginx (TLS, rate limits, LB)
- Scale: one Ollama per GPU + app-level round-robin

## Insight Types

1. channel_performance — ROAS, contribution share, trends
2. budget_recommendation — reallocation with expected revenue impact
3. anomaly — spend/CPM/ROAS deviations
4. benchmark — vs. industry averages
5. summary — executive narrative

## Guardrails

- Always cite numbers from model output; never fabricate metrics
- Include confidence intervals where available
- Template fallback when LLM is down (report.py `_fallback_report`)

*Sources: deep-research workflow (5 agents, 2026-08-01), docs.ollama.com, qwenlm.github.io/blog/qwen2.5, Mistral/Small research.*
