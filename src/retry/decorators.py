# Python AI Toolkit — Fault-Tolerant Execution Layer

> A reusable infrastructure toolkit that extracts common patterns for production LLM workflows into modular, type-safe, and tested components.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)](#)

---

## Problem

Production AI systems routinely fail due to transient remote API instability, network drops, and upstream rate limits (HTTP 429). Standard scripting patterns either fail immediately when encountering these drops or use naive loop retries that overload target clusters, causing cascading system crashes.

---

## Motivation

Building modern AI infrastructure requires moving past brittle, unhandled wrappers. Robust network communication requires an institutional approach to transient faults. By establishing an isolated, high-cohesion retry engine across our portfolio, we ensure that every outgoing call frame handles network faults gracefully, optimizing resource usage and system uptime.

---

## Solution

This project implements a decoupled **Strategy Pattern Engine** that handles backoff math independently from runtime state, using a **Full Jitter Exponential Backoff** algorithm. It exposes two specialized, type-annotated **Decorator Interceptors** (`@retry` and `@retry_async`) to handle both synchronous and asynchronous call flows. This design maintains clear boundaries between mathematical strategy execution, error filtering matrices, and loop scheduling.

---

## Architecture

```mermaid
graph TD
    A[Target Function Execution Call] --> B{Interceptor Matrix}
    B -- Synchronous Function --> C[@retry Decorator Wrapper]
    B -- Asynchronous Coroutine --> D[@retry_async Decorator Wrapper]
    C & D --> E{Exception Whitelist Filter}
    E -- Exception Not Whitelisted --> F[Bubble Up Error / Terminate]
    E -- Exception Whitelisted Matrix Match --> G[Query Strategy Configuration Engine]
    G --> H[Check Attempt Limits]
    H -- Attempts > Max Limit --> I[Raise MaxRetriesExceededError]
    H -- Attempts Allowed --> J[Compute Full Jitter Interval]
    J --> K[Dispatch Lifecycle Callback Hook]
    K --> L[Apply Sleep Frame: Thread/Loop Sleep]
    L --> A
