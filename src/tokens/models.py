"""Shared data models and dataclasses for the tokens package."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenCount:
    """Represents the token and character counts of a text string."""

    token_count: int
    character_count: int


@dataclass(frozen=True)
class ContextStatus:
    """Represents the consumption status of a context window."""

    max_tokens: int
    used_tokens: int
    remaining_tokens: int
    usage_fraction: float


@dataclass(frozen=True)
class TokenBudget:
    """Represents token allocations, consumption, and limits."""

    limit: int
    allocated: int
    consumed: int
    remaining: int


@dataclass(frozen=True)
class CostEstimate:
    """Represents the financial cost estimation for token consumption."""

    input_cost: float
    output_cost: float
    total_cost: float
    currency: str
