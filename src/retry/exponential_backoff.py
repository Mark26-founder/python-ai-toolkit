# ADR-002: Fault-Tolerant Execution Layer via Full Jitter Exponential Backoff

**Date:** 2026-06-30
**Status:** Accepted

---

## Context

Modern AI systems rely heavily on external network IO, including model providers, vector databases, and retrieval APIs. These networks are inherently unreliable and subject to temporal network dropouts, transient server load spikes, and aggressive rate limiting. 

If a system retries failed connection frames instantly or at static linear intervals ($2s, 4s, 6s \dots$), overlapping asynchronous runtime workflows can synchronize their retry schedules. This triggers a "thundering herd" phenomenon, overloading upstream services with dense traffic spikes, prolonging outages, and failing execution states.

## Decision

We will implement a completely decoupled mathematical execution engine using the **Full Jitter Exponential Backoff** strategy, coupled with synchronous and asynchronous structural function wrappers (`@retry` and `@retry_async`). 

The algorithmic formulation calculates a maximum exponential bound based on attempt iterations and caps it at a hard ceiling. It then selects a value uniformly distributed between 0 and that calculated ceiling:

$$Bound = \min(\text{max\_delay}, \text{base\_delay} \times \text{factor}^{\text{attempt}})$$
$$Sleep \sim \mathcal{U}(0, \text{Bound})$$

This formulation randomizes the timing of subsequent network call frames, distributing clustered retry requests into an even, lower-density traffic footprint.

## Rationale

1. **Decoupling Calculation from Execution:** The mathematical engine (`ExponentialBackoff`) is fully state-free and deterministic. To ensure testability as an intentional design goal, the random number generator can be injected or seeded, allowing deterministic unit testing while preserving nondeterministic production behavior without relying on real runtime clock delays.
2. **Algorithmic Choice Justification:** Full Jitter Exponential Backoff is widely recommended in distributed systems because it minimizes synchronized retries ("thundering herd") more effectively than fixed delays or Equal Jitter strategies by maximizing structural randomization across overlapping loops.
3. **Explicit Loop Preservation:** We implement separate sync and async decorator code paths. Sync uses blocking `time.sleep()`, while async utilizes non-blocking `await asyncio.sleep()`. This ensures async loops never block the event runtime thread.
4. **Whitelist Over Catch-All Filtering:** To avoid masking core software bugs (`NameError`, `SyntaxError`), the decorators enforce class-based exception whitelisting, limiting retries strictly to provider-specific transient exceptions.

## Alternatives Considered

| Option | Reason Rejected |
|--------|----------------|
| **Equal Jitter** | Retains a constant baseline delay component ($Sleep = \frac{Bound}{2} + \mathcal{U}(0, \frac{Bound}{2})$). It reduces traffic spike amplitude less effectively than Full Jitter. |
| **Raw Catch-All (`except Exception`)** | Highly dangerous pattern that catches and retries structural application bugs, causing unnecessary loop delays on unrecoverable logic errors. |

## Consequences

* **Easier:** Future portfolio modules can wrap network IO layers safely with predictable configuration objects.
* **Harder:** Developers must explicitly identify and supply exact target exception classes (e.g., `TimeoutError`, `ConnectionError`, `RateLimitError`) to the exception whitelist for optimal safety.
* **Risks Accepted:** Extremely tight retry settings with high maximum bounds under massive workloads can still exhaust local thread capacities if upstream outages persist.

## Future Extensions

* **Retry Budgets:** Tracking systemic failure tokens to halt retries across unrelated operations during macro outages.
* **Circuit Breaker Integration:** A formal state machine to temporarily trip and fast-fail broken connection streams.
* **Adaptive Backoff:** Modulating base delay parameters dynamically using local telemetry feedback loops.
* **Retry Telemetry / OpenTelemetry Hooks:** Exporting structural hook execution traces to monitoring sinks.
