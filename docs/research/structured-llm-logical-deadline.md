# Structured LLM logical deadline and provider-neutral telemetry

Research date: 2026-07-23.  This is a design input for Cloud issue #201,
not an implementation or an ADR.  It uses the Python and LiteLLM primary
sources listed below.  LiteLLM source observations are pinned to current
`main` at `070e19cff82b45026c5a697f683fdd5cdf2d461b`.

## Decision summary

Treat a structured request as **one logical call**, with one monotonic,
absolute deadline.  The budget includes: native-schema attempt(s), all
LiteLLM-managed provider retries and backoff, the explicit JSON-text
fallback, parsing, and Pydantic validation.  `asyncio.timeout_at()` around
that whole operation is the authoritative wall-clock guard.  LiteLLM's
`timeout` is a transport/request limit, not an end-to-end logical deadline.

Native response-schema support is a capability hint, not a guarantee.  If
the native call is unsupported, fails, or returns invalid output, make at
most one explicit JSON-text attempt, then validate the same schema locally.
This fallback is a MemForge strategy transition, not a LiteLLM provider
fallback.

Exact provider-attempt and token accounting cannot be promised solely from a
successful `acompletion()` result or LiteLLM callbacks.  The wrapper can
accurately observe its own native/JSON strategy attempts and total elapsed
time.  LiteLLM callbacks add useful provider-attempt signals, but their
payload and the presence of usage on failures are not a stable, complete
attempt-ledger contract.  If exact retry-attempt accounting is required,
disable LiteLLM retries (`num_retries=0`) and own the retry loop and its
attempt IDs; otherwise record LiteLLM retries as provider-managed/possibly
unobserved.

## Python 3.12 deadline semantics

`asyncio.timeout(delay)` and `asyncio.timeout_at(when)` cancel the **current
task** when overdue.  The context manager converts the cancellation it caused
to built-in `TimeoutError`, which is catchable only outside the context.
`when` is an absolute value from the event loop's monotonic clock; a deadline
in the past fires on the next loop iteration.  The timeout can be inspected,
rescheduled, and safely nested.  Do not swallow `CancelledError` inside the
block: asyncio documents that structured-concurrency components, including
timeouts, rely on cancellation.

Therefore compute one deadline once and share it, rather than starting a new
relative timer for native output, retries, and fallback:

```python
loop = asyncio.get_running_loop()
deadline = loop.time() + logical_budget_s
try:
    async with asyncio.timeout_at(deadline):
        return await run_logical_structured_call(deadline)
except TimeoutError as exc:
    raise StructuredLlmDeadlineExceeded(...) from exc
```

Before *every wrapper-owned* provider call, compute
`remaining_s = deadline - loop.time()`.  If it is non-positive, stop without
starting another call; otherwise pass `timeout=remaining_s` (or a smaller
configured per-request cap).  The outer timeout remains necessary because
LiteLLM's retry/backoff work and local parsing otherwise sit outside a
per-request HTTP timeout.  Cancellation is cooperative: it cannot revoke a
request already accepted by a provider, so timeout is a caller-side latency
and resource bound, not a no-billing guarantee.

Sources: [Python 3.12 asyncio timeouts](https://docs.python.org/3.12/library/asyncio-task.html#timeouts),
[task cancellation guidance](https://docs.python.org/3.12/library/asyncio-task.html#task-cancellation).

## LiteLLM behaviour relevant to this design

### Timeout and retries

LiteLLM documents `num_retries=2` as its retry control and uses Tenacity for
it.  The current async wrapper chooses a retry policy after a failure and
delegates to `acompletion_with_retries`; its implementation uses Tenacity's
`stop_after_attempt(num_retries)`.  The original failed call has already
happened before that helper is invoked, so a design must not infer a precise
total-attempt count from the user-facing setting alone.  It must also leave
headroom for retry backoff within the logical deadline.

Current LiteLLM resolves `timeout` as an HTTP completion timeout with
precedence: model timeout, call `timeout`, `request_timeout`, configured
global request timeout, then 600 seconds.  That source makes no claim that
one timeout spans retry/backoff or a caller's second schema strategy.

Sources: [LiteLLM reliability documentation](https://docs.litellm.ai/docs/completion/reliable_completions),
[async retry wrapper](https://github.com/BerriAI/litellm/blob/070e19cff82b45026c5a697f683fdd5cdf2d461b/litellm/main.py#L5723-L5750),
[async failure-to-retry path](https://github.com/BerriAI/litellm/blob/070e19cff82b45026c5a697f683fdd5cdf2d461b/litellm/utils.py#L1808-L1873),
[HTTP timeout resolution](https://github.com/BerriAI/litellm/blob/070e19cff82b45026c5a697f683fdd5cdf2d461b/litellm/litellm_core_utils/completion_timeout.py#L12-L67).

### Native structured output and fallback

LiteLLM exposes `response_format` and documents model-support discovery.  Its
`supports_response_schema()` function returns `False` rather than raising when
provider/model discovery fails.  That makes capability probing suitable for
choosing a preferred path, but not proof that a gateway alias will accept a
particular schema.  LiteLLM itself does not provide the required semantic
fallback of "remove `response_format`, embed this schema in a prompt, parse
and validate it"; that is application-owned behaviour.

The existing MemForge OSS client already has exactly those two strategies: it
attempts native `response_format`, then on any exception makes one JSON-text
call and validates with the same Pydantic model.  Today each call receives the
full configured timeout and retry budget, so the combined duration is not
bounded by one logical SLA.  Issue #201 should make the strategy state
explicit and place both under the shared deadline.

Sources: [LiteLLM structured-output guide](https://docs.litellm.ai/docs/completion/json_mode),
[capability helper source](https://github.com/BerriAI/litellm/blob/070e19cff82b45026c5a697f683fdd5cdf2d461b/litellm/utils.py#L2241-L2275),
[current MemForge structured client](../../src/memforge/llm/structured.py).

### Callbacks, usage, and retry telemetry

LiteLLM documents callback hooks for pre-API, post-API, success, and failure,
including async success/failure hooks.  Its current logging state records an
`api_call_start_time` for each provider handoff and a separate
`first_api_call_start_time` because retries overwrite the former.  This is
strong evidence that callbacks can provide useful per-handoff observations.

But callback success naturally sees the final returned response; failure
payloads may lack provider usage, and no documented contract says callbacks
form an exactly-once, complete, provider-neutral ledger covering every
network-level retry or token charge.  Provider-side work can also continue
after local cancellation.  Hence:

| Field | Can the structured wrapper state it accurately? | Source of truth |
| --- | --- | --- |
| Logical start/end, deadline, elapsed, terminal result | Yes | Wrapper |
| Native vs JSON-text strategy and fallback reason | Yes | Wrapper |
| Number of MemForge-issued `acompletion` calls | Yes | Wrapper |
| LiteLLM/provider retry count | Only if the wrapper owns retries; otherwise best-effort signal | Wrapper or callback, never inferred from `num_retries` |
| Successful response token usage | Usually when present on final response; preserve as reported | Response/callback payload |
| Failed-attempt token usage or provider billing | No general guarantee | Provider-specific billing/trace system |

Sources: [LiteLLM custom-callback documentation](https://docs.litellm.ai/docs/observability/custom_callback),
[callback base interface](https://github.com/BerriAI/litellm/blob/070e19cff82b45026c5a697f683fdd5cdf2d461b/litellm/integrations/custom_logger.py#L125-L179),
[per-handoff timing state](https://github.com/BerriAI/litellm/blob/070e19cff82b45026c5a697f683fdd5cdf2d461b/litellm/litellm_core_utils/litellm_logging.py#L985-L1004),
[success/failure logging paths](https://github.com/BerriAI/litellm/blob/070e19cff82b45026c5a697f683fdd5cdf2d461b/litellm/litellm_core_utils/litellm_logging.py#L2371-L2460).

## Recommended provider-neutral interface

Keep LiteLLM behind a narrow adapter and expose an application event stream,
not LiteLLM callback payloads, as the durable contract.  Illustrative shape:

```python
async def call_structured(
    request: StructuredRequest,
    *,
    deadline: float,                 # event-loop clock, not wall datetime
    max_provider_attempts: int,
    observer: StructuredCallObserver | None = None,
) -> StructuredResult: ...
```

`StructuredRequest` owns model, messages/schema, and an explicit
`native_then_json_text_once` policy.  `StructuredCallObserver` receives only
normalized events: `logical_started`, `strategy_started`,
`provider_attempt_started`, `provider_attempt_finished`,
`strategy_failed`, `fallback_started`, and `logical_finished`.  Each includes
a logical-call ID, monotonic timestamps, strategy (`native_schema` or
`json_text`), model/provider as LiteLLM reports it, outcome/error category,
remaining budget, and reported usage if available.  The wrapper emits the
logical/strategy events itself; an optional LiteLLM callback adapter may add
provider-attempt observations, labelled `observability="best_effort"`.

There are two valid policy modes:

1. **Strict accounting:** pass `num_retries=0`, classify retryable normalized
   LiteLLM failures in the adapter, and run bounded retries from the wrapper.
   Recompute the remaining request timeout on every attempt.  This is the only
   provider-neutral way to attach exact issued-attempt numbers and strategy
   attribution.
2. **Delegated reliability:** retain LiteLLM `num_retries`, still wrap the
   entire operation in `timeout_at(deadline)`, and record the configured retry
   budget plus callback observations.  Do not claim exact provider attempts,
   retries, or failed-attempt tokens.

For issue #201, choose the first mode if its acceptance criteria require
accurate retry telemetry; otherwise choose the second for a smaller change but
document its observability boundary.  Both modes must use the outer absolute
deadline and cap the JSON-text fallback to one application-owned transition.

## Risks and tests to require

- A per-attempt `timeout_s` reset for native and fallback can consume roughly
  twice the budget before internal retries/backoff; test elapsed time across
  native failure, retry delay, JSON fallback, and validation.
- Catching `CancelledError` inside the deadline scope breaks `timeout_at`'s
  conversion and cancellation semantics; test that the boundary exposes the
  domain timeout and does not start fallback after expiry.
- A native schema rejection is not necessarily transient.  Limit JSON fallback
  to once and retain the native failure category for auditability.
- A response may be valid but contain no usage, and failed/cancelled attempts
  may have consumed billable tokens.  Report missing/unknown rather than zero.
- Test callbacks only as supplemental telemetry: their absence or duplication
  must not change request correctness, attempt limits, or durable accounting.
- Use fake LiteLLM adapters to prove the same deadline and normalized event
  contract for every provider; no provider-specific branches should decide the
  logical budget, schema fallback, or event schema.
