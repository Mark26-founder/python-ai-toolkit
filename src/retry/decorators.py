# Python AI Toolkit

> A lightweight Python toolkit providing reusable infrastructure for modern AI/LLM applications, including retry mechanisms, token management, parsing utilities, configuration handling, and other reusable engineering components.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)](#)

---

## Minimal Usage Example

```python
from retry.decorators import RetryPolicy, retry

# Configure specific error boundaries to prevent catching core runtime errors
api_policy = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    exceptions_whitelist=(TimeoutError, ConnectionError),
)

@retry(policy=api_policy)
def fetch_api_payload():
    # Transient failures within the whitelist will be automatically retried
    return "API Response"
