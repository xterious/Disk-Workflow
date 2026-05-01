from dataclasses import asdict, dataclass
from typing import Any


ALLOWED_ACTIONS = {
    "CHECK_DISK",
    "GET_TEMP_FILES",
    "CLEAN_TEMP_FILES",
    "FIND_LARGE_FILES",
}


@dataclass
class PlanStep:
    action: str
    requires_confirmation: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanStep":
        action = data.get("action")
        requires_confirmation = data.get("requires_confirmation")

        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported action: {action}")
        if not isinstance(requires_confirmation, bool):
            raise ValueError(
                f"requires_confirmation must be a boolean for action {action}"
            )

        return cls(
            action=action,
            requires_confirmation=requires_confirmation,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Plan:
    intent: str
    confidence: float
    steps: list[PlanStep]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        intent = data.get("intent")
        confidence = data.get("confidence")
        steps = data.get("steps")

        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent must be a non-empty string")
        if not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        if not isinstance(steps, list):
            raise ValueError("steps must be a list")

        return cls(
            intent=intent.strip(),
            confidence=float(confidence),
            steps=[PlanStep.from_dict(step) for step in steps],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "steps": [step.to_dict() for step in self.steps],
        }
