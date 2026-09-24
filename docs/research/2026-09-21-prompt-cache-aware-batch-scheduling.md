# Prompt-cache-aware batch scheduling

Research date: 2026-09-21. This is an ADR input, not an implementation or a
normative runtime contract. It considers only provider prompt caches; MemForge
work identity, dependency order, validation and lifecycle commit remain
unchanged. Its v1 recommendation (bounded concurrency, no leader barrier) is
adopted as a property of the LLM batch runner in
[ADR 0036](../adr/0036-separate-semantic-work-from-inference-executors.md).

## Recommendation

Keep the scheduler small. The recommended v1 is bounded concurrency without a
leader barrier:

```text
dependency-ready work
  -> existing global concurrency limit
  -> prefer adjacent dispatch for calls with the same derived exact-prefix digest
  -> stateful lanes remain serial and naturally warm their later calls
  -> existing complete-work validation and atomic commit
```

Do not add a domain `cache_prefix_key`, durable cache state, TTL registry, cache
job, or a second business batching abstraction. The Structured LLM adapter can
derive a conservative in-memory digest from the actual route, model, cache
mode/TTL, breakpoint and serialized prefix bytes. The digest is only a local
grouping hint; provider-reported usage is the only evidence of a write or hit.

Use one global semaphore. Do not delay a request to collect a larger cache
group. A group of one, a prefix below the route's model-specific minimum, or a
route whose prompt-cache support has not been verified goes straight through
the semaphore. Dependency lanes remain serial; their first call can populate a
cache that the next state-dependent call reuses. Independent lanes and
independent calls remain concurrent.

The reason not to add a leader barrier in v1 is latency. Anthropic explicitly
states that a cache entry becomes available after the first response begins and
instructs clients that need parallel cache hits to wait for that point before
sending the other requests. Thus “warm one, then fan out” is documented Claude
behavior, not an inference
([Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).
But the current MemForge call awaits a non-streaming `litellm.acompletion(...)`;
it has no response-begin event and would have to wait for the leader's complete
generation before releasing followers
([current structured client](../../src/memforge/llm/structured.py)). For a
latency-sensitive batch, that can erase the benefit of independent concurrency.
Bounded concurrency also creates natural cache reuse when a same-prefix group is
larger than the semaphore: later waves start after an earlier call has completed.

If a later streaming transport exposes Anthropic's first `message_start`, add a
small per-run single-flight gate: the first real call for a derived prefix is the
leader, same-prefix followers wait for response-start, then all followers use
the same global semaphore. Open the gate on leader success or failure so the
optimization cannot suppress work. Do not issue a dummy generation solely to
warm the cache. A full-response barrier on the current non-streaming transport
should be opt-in only if a bounded route measurement proves that its cost saving
is worth the added wall time.

If that optional gate is introduced, one per-run map from derived digest to an
`asyncio.Event` or `Future` is enough. Delete it when the run ends. There is no
need to model eviction: a miss is behaviorally valid, and a provider may evict
or route away from an eligible cache even inside its nominal TTL.

## Why this boundary is sufficient

Anthropic caches the exact cumulative prefix in `tools`, `system`, then
`messages` order. A breakpoint writes only the prefix ending at that point; a
later lookup searches for a prior write, and changing content before the
breakpoint changes the prefix. The default TTL is five minutes, a one-hour TTL
is available at higher write cost, and model-specific minimum prefix sizes
apply. Inputs below the minimum are accepted without caching. Anthropic exposes
`cache_creation_input_tokens` and `cache_read_input_tokens`, which means the
scheduler should measure outcomes rather than infer them from its local digest
([Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).

The provider's asynchronous Batch API is not a substitute for this manager.
Anthropic says batch requests run concurrently and in arbitrary order, so cache
hits inside a Message Batch are best effort; it reports typical observed hit
rates of 30% to 98%. Batch prewarming with `max_tokens: 0` is unsupported, and
long batch execution may require the one-hour TTL
([Anthropic Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing)).
Amazon Bedrock currently states that prompt caching is unavailable for its
batch inference API. For normal inference, Bedrock also says an eligible cache
checkpoint does not guarantee a hit, cross-region routing can increase cache
writes, and callers must inspect `cacheReadInputTokens` and
`cacheWriteInputTokens`
([Amazon Bedrock prompt caching](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)).

LiteLLM can pass Anthropic `cache_control` markers, translate them for Bedrock,
and normalize cache usage into `prompt_tokens_details.cached_tokens` plus
Anthropic cache-creation tokens. That establishes transport support, not that a
particular SAP/Bedrock route preserves response-start availability, TTL, or hit
behavior. Enable the prefix gate only after the configured route returns the
expected cache usage fields
([LiteLLM prompt caching](https://docs.litellm.ai/docs/completion/prompt_caching)).
The provider/model threshold tables in gateway documentation can lag the owning
provider, so threshold admission should follow the configured provider's current
model contract and be confirmed by usage. This research found no public SAP AI
Core documentation that promises prompt-cache pass-through or Anthropic's
response-start visibility semantics; treat an SAP route as unverified until a
bounded live check establishes them.

OpenAI is a useful comparison, not a portable contract. Current OpenAI
documentation says exact-prefix reuse and cache routing are provider-managed;
cache keys do not guarantee a hit. GPT-5.6 and later additionally provide an
explicit `prompt_cache_options.prewarm: true` Responses API request that writes
the cache without generating output. If MemForge later supports that exact
route, the adapter can use the provider primitive, but the generic scheduler
should still use real leader work by default and should not invent a portable
prewarm operation
([OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)).

TypeSafe/Jev has a different optimization boundary. Its official guidance for
many independent questions over the same state is to send them in one System
One request; the documented API surface exposes `/v1/models` and
`/v1/systemone`, with ordinary input/output usage and no cross-request cache
key, TTL, cache-write, or cache-hit contract. Jev work should therefore batch
eligible independent questions within one request rather than enter this
cross-request prefix gate
([TypeSafe parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions),
[TypeSafe OpenAPI](https://api.typesafe.ai/openapi.json)).

## Minimal acceptance evidence

Before enabling the gate on a deployed route, run one bounded comparison with
the same rendered prefix:

- immediate bounded fan-out;
- one leader followed by bounded fan-out;
- identical work count, model, prefix, suffix distribution and validation;
- reported cache writes/reads, wall time and input cost captured for both.

Keep the gate only when the actual route shows a material net benefit. In
particular, waiting for a full non-streaming leader trades wall-clock latency for
more likely cache reads. The result should decide whether that trade is useful;
nominal provider support alone should not.
