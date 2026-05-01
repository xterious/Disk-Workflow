import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }
  return data;
}

function MessageBubble({ message }) {
  return (
    <div className={`message-row ${message.role}`}>
      <div className={`message-bubble ${message.role}`}>
        <div className="message-content">{message.text}</div>
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [pendingConfirmation, setPendingConfirmation] = useState(false);
  const [pendingStep, setPendingStep] = useState(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  function applyState(state) {
    setMessages(state.messages || []);
    setPendingConfirmation(Boolean(state.pending_confirmation));
    setPendingStep(state.pending_step || null);
  }

  useEffect(() => {
    api("/api/state", { method: "GET" })
      .then(applyState)
      .catch((error) => {
        setMessages([
          {
            role: "assistant",
            text: `Unable to load chat state: ${error.message}`
          }
        ]);
      });
  }, []);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) {
      return;
    }

    node.scrollTo({
      top: node.scrollHeight,
      behavior: "smooth"
    });
  }, [messages, pendingConfirmation]);

  async function sendMessage(event) {
    event?.preventDefault();

    const message = input.trim();
    if (!message || busy || pendingConfirmation) {
      return;
    }

    setBusy(true);
    setInput("");

    try {
      const data = await api("/api/message", {
        method: "POST",
        body: JSON.stringify({ message })
      });
      applyState(data);
    } catch (error) {
      setMessages((current) => [
        ...current,
        { role: "assistant", text: error.message }
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmation(approve) {
    if (busy) {
      return;
    }

    setBusy(true);
    try {
      const data = await api("/api/confirm", {
        method: "POST",
        body: JSON.stringify({ approve })
      });
      applyState(data);
    } catch (error) {
      setMessages((current) => [
        ...current,
        { role: "assistant", text: error.message }
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function newChat() {
    if (busy) {
      return;
    }

    setBusy(true);
    try {
      const data = await api("/api/reset", { method: "POST" });
      applyState(data);
      setInput("");
    } catch (error) {
      setMessages((current) => [
        ...current,
        { role: "assistant", text: error.message }
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="backdrop-glow backdrop-glow-a" />
      <div className="backdrop-glow backdrop-glow-b" />

      <main className="app-card">
        <header className="app-header">
          <div>
            <p className="eyebrow">Disk Cleanup Assistant</p>
            <h1>Chat-driven cleanup, without the noise.</h1>
            <p className="subtitle">
              Ask in plain English. You will only see your prompt and the final response.
            </p>
          </div>
          <button className="secondary-button" onClick={newChat} disabled={busy}>
            New Chat
          </button>
        </header>

        <section className="chat-panel">
          <div ref={scrollRef} className="chat-scroll">
            {messages.map((message, index) => (
              <MessageBubble
                key={`${message.role}-${index}-${message.text}`}
                message={message}
              />
            ))}
          </div>

          {pendingConfirmation && pendingStep ? (
            <div className="confirmation-strip">
              <div>
                <div className="confirmation-title">Approval needed</div>
                <div className="confirmation-text">
                  {pendingStep.action} is waiting for your confirmation.
                </div>
              </div>
              <div className="confirmation-actions">
                <button
                  className="secondary-button"
                  onClick={() => handleConfirmation(false)}
                  disabled={busy}
                >
                  Skip
                </button>
                <button
                  className="primary-button"
                  onClick={() => handleConfirmation(true)}
                  disabled={busy}
                >
                  Approve
                </button>
              </div>
            </div>
          ) : null}

          <form className="composer" onSubmit={sendMessage}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  sendMessage(event);
                }
              }}
              placeholder="Try 'free up disk space' or 'find large files'"
              disabled={busy || pendingConfirmation}
              rows={1}
            />
            <button
              type="submit"
              className="primary-button send-button"
              disabled={busy || pendingConfirmation || !input.trim()}
            >
              Send
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
