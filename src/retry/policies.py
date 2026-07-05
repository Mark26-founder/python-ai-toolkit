"""Configuration policy managing retry behaviors and limits."""

import logging
from dataclasses import dataclass, field
from typing import Sequence, Type

from retry.callbacks import AfterRetryHook, BeforeRetryHook, OnFailureHook, OnSuccessHook
from retry.exceptions import RetryConfigurationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration blueprint defining operational boundaries for retrying operations.

    Raises:
        RetryConfigurationError: If any boundary conditions are violated during instantiation.
    """
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_factor: float = 2.0
    jitter_enabled: bool = True
    retry_exceptions: Sequence[Type[Exception]] = field(default_factory=lambda: (Exception,))
    
    # Lifecycle Hooks
    before_retry: BeforeRetryHook | None = None
    after_retry: AfterRetryHook | None = None
    on_success: OnSuccessHook | None = None
    on_failure: OnFailureHook | None = None

    def __post_init__(self) -> None:
        """Validates configuration parameters against functional boundaries."""
        if self.max_attempts < 1:
            raise RetryConfigurationError(
                f"max_attempts must be greater than or equal to 1, got {self.max_attempts}"
            )
        if self.base_delay < 0:
            raise RetryConfigurationError(
                f"base_delay must be non-negative, got {self.base_delay}"
            )
        if self.max_delay < self.base_delay:
            raise RetryConfigurationError(
                f"max_delay ({self.max_delay}) cannot be less than base_delay ({self.base_delay})"
            )
        if self.exponential_factor < 1.0:
            raise RetryConfigurationError(
                f"exponential_factor must be >= 1.0, got {self.exponential_factor}"
            )
        if not self.retry_exceptions:
            raise RetryConfigurationError(
                "retry_exceptions cannot be an empty sequence. Specify at least one Exception type."
            )
