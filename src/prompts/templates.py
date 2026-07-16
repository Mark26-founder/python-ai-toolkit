"""Reusable prompt templates with variable substitution and validation."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set
from .exceptions import TemplateError, VariableError

# Matches {variable_name} placeholders
_PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class PromptTemplate:
    """An immutable prompt template supporting variable placeholders."""

    template: str
    defaults: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.template.strip():
            raise TemplateError("Template string cannot be empty.")

    def variables(self) -> Set[str]:
        """Discovers all placeholder variable names in the template.

        Returns:
            A set of variable name strings.
        """
        return set(_PLACEHOLDER_PATTERN.findall(self.template))

    def required_variables(self) -> Set[str]:
        """Returns the set of variables that have no default value.

        Returns:
            A set of required variable name strings.
        """
        return self.variables() - set(self.defaults.keys())

    def validate(self, variables: Dict[str, Any]) -> None:
        """Validates that all required variables are provided.

        Args:
            variables: Dictionary of variable names to values.

        Raises:
            VariableError: If any required variables are missing.
        """
        missing = self.required_variables() - set(variables.keys())
        if missing:
            raise VariableError(
                f"Missing required template variables: {', '.join(sorted(missing))}"
            )

    def render(self, **variables: Any) -> str:
        """Renders the template with the given variables.

        Args:
            **variables: Variable values to substitute.

        Returns:
            The rendered string.

        Raises:
            VariableError: If any required variables are missing.
        """
        merged = {**self.defaults, **variables}
        self.validate(merged)
        return self.template.format_map(merged)
