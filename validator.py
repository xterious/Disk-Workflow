from schemas import ALLOWED_ACTIONS, Plan


def is_safe(action):
    return action in ALLOWED_ACTIONS


def validate_plan(plan_data):
    plan = Plan.from_dict(plan_data)

    if not 0 <= plan.confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")

    steps = plan.steps
    actions = [step.action for step in steps]

    if actions and actions[0] != "CHECK_DISK":
        raise ValueError("CHECK_DISK must be the first step")

    if "CLEAN_TEMP_FILES" in actions:
        clean_index = actions.index("CLEAN_TEMP_FILES")
        if "GET_TEMP_FILES" not in actions[:clean_index]:
            raise ValueError(
                "GET_TEMP_FILES must appear before CLEAN_TEMP_FILES"
            )

    for step in steps:
        if step.action == "CLEAN_TEMP_FILES" and not step.requires_confirmation:
            raise ValueError(
                "CLEAN_TEMP_FILES must require confirmation"
            )
        if step.action != "CLEAN_TEMP_FILES" and step.requires_confirmation:
            raise ValueError(
                f"{step.action} should not require confirmation"
            )

    return plan.to_dict()
