from schemas import ALLOWED_ACTIONS


def adjust_confidence(plan):
    confidence = float(plan.get("confidence", 0))
    steps = plan.get("steps", [])

    if not steps:
        confidence -= 0.3

    for step in steps:
        if step.get("action") not in ALLOWED_ACTIONS:
            confidence -= 0.2

    if steps and steps[0].get("action") == "CHECK_DISK":
        confidence += 0.05

    if "CLEAN_TEMP_FILES" in [step.get("action") for step in steps]:
        confidence = min(confidence, 1.0)

    return max(0.0, min(confidence, 1.0))
