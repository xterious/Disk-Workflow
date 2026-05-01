from tools.disk import check_disk
from tools.files import find_large_files
from tools.temp import clean_temp, get_temp_size
from validator import is_safe


CONFIDENCE_THRESHOLD = 0.7


def run_action(action_name):
    actions = {
        "CHECK_DISK": check_disk,
        "GET_TEMP_FILES": get_temp_size,
        "CLEAN_TEMP_FILES": clean_temp,
        "FIND_LARGE_FILES": find_large_files,
    }

    action = actions.get(action_name)
    if action is None:
        raise ValueError(f"Unknown action: {action_name}")
    return action()


def execute_step(action_name):
    if not is_safe(action_name):
        return {
            "action": action_name,
            "status": "skipped",
            "message": f"Skipped unsafe action: {action_name}",
        }

    result = run_action(action_name)
    return {
        "action": action_name,
        "status": "completed",
        "message": result,
    }


def continue_plan_execution(plan, start_index=0, confirmed_actions=None, skipped_actions=None):
    confidence = float(plan.get("confidence", 0))
    confirmed_actions = set(confirmed_actions or [])
    skipped_actions = set(skipped_actions or [])

    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "status": "needs_clarification",
            "confidence": confidence,
            "results": [],
            "pending_confirmation": None,
            "next_index": start_index,
        }

    results = []

    for index, step in enumerate(plan.get("steps", [])[start_index:], start=start_index):
        action_name = step["action"]

        if not is_safe(action_name):
            results.append(
                {
                    "action": action_name,
                    "status": "skipped",
                    "message": f"Skipped unsafe action: {action_name}",
                }
            )
            continue

        if action_name in skipped_actions:
            results.append(
                {
                    "action": action_name,
                    "status": "skipped",
                    "message": f"Skipped {action_name}",
                }
            )
            continue

        if step.get("requires_confirmation", False) and action_name not in confirmed_actions:
            return {
                "status": "awaiting_confirmation",
                "confidence": confidence,
                "results": results,
                "pending_confirmation": step,
                "next_index": index,
            }

        results.append(execute_step(action_name))

    return {
        "status": "completed",
        "confidence": confidence,
        "results": results,
        "pending_confirmation": None,
        "next_index": len(plan.get("steps", [])),
    }


def execute_plan(plan):
    print(f"Confidence: {float(plan.get('confidence', 0)):.2f}")

    next_index = 0
    confirmed_actions = set()
    skipped_actions = set()

    while True:
        execution = continue_plan_execution(
            plan,
            start_index=next_index,
            confirmed_actions=confirmed_actions,
            skipped_actions=skipped_actions,
        )

        if execution["status"] == "needs_clarification":
            print(f"Low confidence: {execution['confidence']:.2f}")
            print("Execution stopped. Please clarify your request.")
            return

        for result in execution["results"]:
            print(f"\nRunning {result['action']}...")
            print(result["message"])

        if execution["status"] == "completed":
            return

        pending_step = execution["pending_confirmation"]
        action_name = pending_step["action"]
        answer = input(
            f"Confirm action {action_name}? Type 'yes' to continue: "
        ).strip().lower()

        if answer == "yes":
            confirmed_actions.add(action_name)
        else:
            skipped_actions.add(action_name)

        next_index = execution["next_index"]
