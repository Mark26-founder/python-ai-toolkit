# ADR-002: Fault-Tolerant Execution Layer via Full Jitter Exponential Backoff

**Date:** 2026-06-30
**Status:** Accepted

---

## Context

Production AI systems rely heavily on external network IO (LLM model providers, vector databases, and retrieval APIs). These networks are inherently unreliable and subject to temporal network dropouts, transient server load spikes, and aggressive rate limiting (e.g., HTTP 429). 

If a system retries failed connection frames instantly or at static linear intervals ($2s, 4s, 6s \dots$), overlapping asynchronous runtime workflows can synchronize their retry schedules. This triggers a "Thundering Herd" phenomenon, blinding upstream services with dense traffic spikes, prolonging outages, and failing execution states.

## Decision

We will implement a completely decoupled, deterministic mathematical execution engine using the **Full Jitter Exponential Backoff** strategy, coupled with synchronous and asynchronous structural function wrappers (`@retry` and `@retry_async`). 

The algorithmic formulation calculates a maximum exponential bound based on attempt iterations and caps it at a hard ceiling. It then selects a value uniformly distributed between 0 and that calculated ceiling:

$$Bound = \min(\text{max\_delay}, \text{base\_delay} \times \text{factor}^{\text{attempt}})$$
$$Sleep \sim \mathcal{U}(0, \text{Bound})$$

This formulation randomizes the timing of subsequent network call frames, distributing clustered retry requests into an even, lower-density traffic footprint.

## Rationale

1. **Decoupling Calculation from Execution:** The mathematical engine (`ExponentialBackoff`) is fully state-free and deterministic when seeded. This design allows it to be evaluated instantly in testing suites without relying on real runtime clock delays.
2. **Explicit Loop Preservation:** We implement separate sync and async decorator code paths. Sync uses blocking `time.sleep()`, while async utilizes non-blocking `await asyncio.sleep()`. This ensures async loops never block the event runtime thread.
3. **Whitelist Over Catch-All Filtering:** To avoid masking core software bugs (`NameError`, `SyntaxError`), the decorators enforce class-based exception whitelisting, limiting retries strictly to expected network fault boundaries.

## Alternatives Considered

| Option | Reason Rejected |
|--------|----------------|
| **Equal Jitter** | Retains a constant baseline delay component ($Sleep = \frac{Bound}{2} + \mathcal{U}(0, \frac{Bound}{2})$). It reduces traffic spike amplitude less effectively than Full Jitter. |
| **Raw Catch-All (`except Exception`)** | Highly dangerous pattern that catches and retries structural application bugs, causing unnecessary loop delays on unrecoverable logic errors. |

## Consequences

* **Easier:** Future portfolio modules can wrap network IO layers safely with predictable configuration objects.
* **Harder:** Developers must explicitly identify and supply exact target exception classes (`openai.RateLimitError`, etc.) to the exception whitelist for optimal safety.
* **Risks Accepted:** Extremely tight retry settings with high maximum bounds under massive workloads can still exhaust local thread capacities if upstream outages persist.
