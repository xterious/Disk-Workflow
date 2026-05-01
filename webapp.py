from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from confidence import adjust_confidence
from executor import continue_plan_execution
from planner import create_plan


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Disk Cleanup Chatbot")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.state.chat_state = {
    "messages": [],
    "pending_plan": None,
    "pending_index": 0,
    "confirmed_actions": [],
    "skipped_actions": [],
}


class ChatMessageRequest(BaseModel):
    message: str


class ConfirmationRequest(BaseModel):
    approve: bool


GREETING_INPUTS = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "good morning",
    "good afternoon",
    "good evening",
}


def _default_messages():
    return [
        {
            "role": "assistant",
            "kind": "text",
            "text": (
                "I can help analyze disk usage, estimate reclaimable temp space, "
                "clean temp files with confirmation, and find large files. "
                "Try: 'free up disk space' or 'check my disk usage'."
            ),
        }
    ]


def _is_greeting(message):
    normalized = " ".join(message.lower().strip().split())
    return normalized in GREETING_INPUTS


def _greeting_message():
    return {
        "role": "assistant",
        "kind": "text",
        "text": (
            "Hi! How can I help? I can check disk usage, estimate reclaimable "
            "temp space, clean temp files with confirmation, or find large files."
        ),
    }


def _chat_state():
    state = app.state.chat_state
    if not state["messages"]:
        state["messages"] = _default_messages()
    return state


def _plan_message(plan):
    return {
        "role": "assistant",
        "kind": "internal_plan",
        "hidden": True,
        "text": "Here is the execution plan I generated.",
        "plan": plan,
    }


def _result_messages(results):
    messages = []
    for result in results:
        messages.append(
            {
                "role": "assistant",
                "kind": "internal_result",
                "hidden": True,
                "action": result["action"],
                "status": result["status"],
                "text": result["message"],
            }
        )
    return messages


def _pending_message(step):
    return {
        "role": "assistant",
        "kind": "internal_confirmation",
        "hidden": True,
        "action": step["action"],
        "text": (
            f"{step['action']} needs confirmation before I continue. "
            "Approve this step?"
        ),
    }


def _final_summary_message(results, status):
    if status == "needs_clarification":
        return {
            "role": "assistant",
            "kind": "text",
            "text": "I’m not confident enough to act yet. Please be a bit more specific.",
        }

    if status == "awaiting_confirmation":
        return {
            "role": "assistant",
            "kind": "text",
            "text": (
                "I’ve checked the safe steps. Cleaning temp files needs your approval "
                "before I continue."
            ),
        }

    visible_results = [result["message"] for result in results if result["status"] == "completed"]
    if not visible_results:
        return {
            "role": "assistant",
            "kind": "text",
            "text": "Done.",
        }

    return {
        "role": "assistant",
        "kind": "text",
        "text": "\n\n".join(visible_results),
    }


def _state_payload(state):
    pending = state["pending_plan"] is not None
    pending_step = None
    if pending:
        pending_step = state["pending_plan"]["steps"][state["pending_index"]]

    return {
        "messages": [
            message for message in state["messages"] if not message.get("hidden", False)
        ],
        "pending_confirmation": pending,
        "pending_step": pending_step,
    }


def _run_plan_into_state(state, plan, start_index=0):
    execution = continue_plan_execution(
        plan,
        start_index=start_index,
        confirmed_actions=state["confirmed_actions"],
        skipped_actions=state["skipped_actions"],
    )

    state["messages"].extend(_result_messages(execution["results"]))

    if execution["status"] == "needs_clarification":
        state["pending_plan"] = None
        state["pending_index"] = 0
        state["confirmed_actions"] = []
        state["skipped_actions"] = []
        state["messages"].append(
            _final_summary_message(execution["results"], execution["status"])
        )
        return

    if execution["status"] == "awaiting_confirmation":
        state["pending_plan"] = plan
        state["pending_index"] = execution["next_index"]
        state["messages"].append(_pending_message(execution["pending_confirmation"]))
        state["messages"].append(
            _final_summary_message(execution["results"], execution["status"])
        )
        return

    state["pending_plan"] = None
    state["pending_index"] = 0
    state["confirmed_actions"] = []
    state["skipped_actions"] = []
    state["messages"].append(_final_summary_message(execution["results"], execution["status"]))


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/state")
def get_state():
    state = _chat_state()
    return JSONResponse(_state_payload(state))


@app.post("/api/message")
def post_message(payload: ChatMessageRequest):
    state = _chat_state()

    if state["pending_plan"] is not None:
        raise HTTPException(
            status_code=409,
            detail="Please confirm or skip the pending action first.",
        )

    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    state["messages"].append(
        {
            "role": "user",
            "kind": "text",
            "text": user_message,
        }
    )

    if _is_greeting(user_message):
        state["messages"].append(_greeting_message())
        return JSONResponse(_state_payload(state))

    try:
        plan = create_plan(user_message)
        plan["confidence"] = adjust_confidence(plan)
    except Exception as exc:
        state["messages"].append(
            {
                "role": "assistant",
                "kind": "error",
                "text": f"Planning failed: {exc}",
            }
        )
        return JSONResponse(_state_payload(state), status_code=200)

    state["messages"].append(_plan_message(plan))
    _run_plan_into_state(state, plan)

    return JSONResponse(_state_payload(state))


@app.post("/api/confirm")
def post_confirm(payload: ConfirmationRequest):
    state = _chat_state()
    plan = state["pending_plan"]

    if plan is None:
        raise HTTPException(status_code=409, detail="No pending action.")

    pending_step = plan["steps"][state["pending_index"]]
    action_name = pending_step["action"]

    state["messages"].append(
        {
            "role": "user",
            "kind": "text",
            "text": "Yes, continue." if payload.approve else "No, skip it.",
        }
    )

    if payload.approve:
        state["confirmed_actions"].append(action_name)
    else:
        state["skipped_actions"].append(action_name)

    _run_plan_into_state(
        state,
        plan,
        start_index=state["pending_index"],
    )

    return JSONResponse(_state_payload(state))


@app.post("/api/reset")
def post_reset():
    app.state.chat_state = {
        "messages": _default_messages(),
        "pending_plan": None,
        "pending_index": 0,
        "confirmed_actions": [],
        "skipped_actions": [],
    }
    state = app.state.chat_state
    return JSONResponse(_state_payload(state))
