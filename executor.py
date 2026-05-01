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


def execute_plan(plan):
    confidence = float(plan.get("confidence", 0))

    if confidence < CONFIDENCE_THRESHOLD:
        print(f"Low confidence: {confidence:.2f}")
        print("Execution stopped. Please clarify your request.")
        return

    print(f"Confidence: {confidence:.2f}")

    for step in plan.get("steps", []):
        action_name = step["action"]

        if not is_safe(action_name):
            print(f"Skipped unsafe action: {action_name}")
            continue

        if step.get("requires_confirmation", False):
            answer = input(
                f"Confirm action {action_name}? Type 'yes' to continue: "
            ).strip().lower()
            if answer != "yes":
                print(f"Skipped {action_name}")
                continue

        print(f"\nRunning {action_name}...")
        result = run_action(action_name)
        print(result)
