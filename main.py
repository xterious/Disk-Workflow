import json

from confidence import adjust_confidence
from executor import execute_plan
from planner import create_plan


def main():
    user_input = input("Enter request: ")

    plan = create_plan(user_input)
    plan["confidence"] = adjust_confidence(plan)

    print("Plan:")
    print(json.dumps(plan, indent=2))

    execute_plan(plan)


if __name__ == "__main__":
    main()
