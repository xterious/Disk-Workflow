const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chatForm");
const inputEl = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const resetBtn = document.getElementById("resetBtn");
const confirmationBar = document.getElementById("confirmationBar");
const confirmationText = document.getElementById("confirmationText");
const approveBtn = document.getElementById("approveBtn");
const skipBtn = document.getElementById("skipBtn");

function renderPlan(plan) {
  const steps = plan.steps
    .map((step) => {
      const suffix = step.requires_confirmation ? " (confirmation required)" : "";
      return `<li><strong>${escapeHtml(step.action)}</strong>${suffix}</li>`;
    })
    .join("");

  return `
    <div class="plan-card">
      <div class="plan-meta">
        <span><strong>Intent:</strong> ${escapeHtml(plan.intent)}</span>
        <span><strong>Confidence:</strong> ${plan.confidence.toFixed(2)}</span>
      </div>
      <ol class="plan-steps">${steps}</ol>
    </div>
  `;
}

function renderMessage(message) {
  const row = document.createElement("article");
  row.className = `message-row ${message.role}`;

  const wrap = document.createElement("div");
  wrap.className = `message ${message.role} ${message.kind === "error" ? "error" : ""}`;

  let label = message.role === "user" ? "You" : "Assistant";
  if (message.kind === "plan") {
    label = "Plan";
  } else if (message.kind === "result") {
    label = message.action;
  } else if (message.kind === "confirmation") {
    label = "Confirmation";
  }

  let inner = `
    <div class="message-label">${label}</div>
    <div class="message-body">${escapeHtml(message.text || "")}</div>
  `;

  if (message.kind === "plan" && message.plan) {
    inner += renderPlan(message.plan);
  }

  wrap.innerHTML = inner;
  row.appendChild(wrap);
  return row;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function updateConfirmation(state) {
  inputEl.disabled = state.pending_confirmation;
  sendBtn.disabled = state.pending_confirmation;

  if (!state.pending_confirmation || !state.pending_step) {
    confirmationBar.classList.add("hidden");
    return;
  }

  confirmationText.textContent = `${state.pending_step.action} is waiting for your approval.`;
  confirmationBar.classList.remove("hidden");
}

function renderState(state) {
  messagesEl.innerHTML = "";
  state.messages.forEach((message) => {
    messagesEl.appendChild(renderMessage(message));
  });
  updateConfirmation(state);
  requestAnimationFrame(() => {
    messagesEl.scrollTo({
      top: messagesEl.scrollHeight,
      behavior: "smooth",
    });
  });
}

async function fetchState() {
  const response = await fetch("/api/state");
  const state = await response.json();
  renderState(state);
}

async function sendMessage(message) {
  sendBtn.disabled = true;
  try {
    const response = await fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const state = await response.json();
    if (!response.ok) {
      throw new Error(state.detail || "Request failed.");
    }
    renderState(state);
  } catch (error) {
    window.alert(error.message);
  } finally {
    if (!inputEl.disabled) {
      sendBtn.disabled = false;
    }
  }
}

async function sendConfirmation(approve) {
  approveBtn.disabled = true;
  skipBtn.disabled = true;
  try {
    const response = await fetch("/api/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approve }),
    });
    const state = await response.json();
    if (!response.ok) {
      throw new Error(state.detail || "Confirmation failed.");
    }
    renderState(state);
  } catch (error) {
    window.alert(error.message);
  } finally {
    approveBtn.disabled = false;
    skipBtn.disabled = false;
  }
}

async function resetChat() {
  const response = await fetch("/api/reset", { method: "POST" });
  const state = await response.json();
  renderState(state);
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = inputEl.value.trim();
  if (!message) {
    return;
  }

  inputEl.value = "";
  await sendMessage(message);
});

approveBtn.addEventListener("click", async () => {
  await sendConfirmation(true);
});

skipBtn.addEventListener("click", async () => {
  await sendConfirmation(false);
});

resetBtn.addEventListener("click", async () => {
  await resetChat();
});

inputEl.addEventListener("keydown", async (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (sendBtn.disabled || inputEl.disabled) {
      return;
    }

    const message = inputEl.value.trim();
    if (!message) {
      return;
    }

    inputEl.value = "";
    await sendMessage(message);
  }
});

fetchState();
