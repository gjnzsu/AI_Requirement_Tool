"""Settings for requirement quality review and maturity evaluation."""

from __future__ import annotations

from dataclasses import dataclass


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes", "on"}


@dataclass(frozen=True)
class RequirementEvaluationSettings:
    """Feature flags for requirement review phases."""

    evaluation_enabled: bool = True
    gate_enabled: bool = False
    judge_enabled: bool = False

    @classmethod
    def from_config(cls, config) -> "RequirementEvaluationSettings":
        return cls(
            evaluation_enabled=_as_bool(
                getattr(config, "REQUIREMENT_EVALUATION_ENABLED", True),
                default=True,
            ),
            gate_enabled=_as_bool(
                getattr(config, "REQUIREMENT_EVALUATION_GATE_ENABLED", False),
                default=False,
            ),
            judge_enabled=_as_bool(
                getattr(config, "REQUIREMENT_JUDGE_ENABLED", False),
                default=False,
            ),
        )
