// components/ChatWindow.jsx
import React, { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import { streamChat } from "../api/client";
import { useT } from "../i18n";

const LANGUAGES = [
  "Auto-detect",
  "Hindi",
  "Bengali",
  "Marathi",
  "Tamil",
  "Telugu",
  "Gujarati",
  "Kannada",
  "Malayalam",
  "Punjabi",
  "Urdu",
  "English",
];

const BORDER = "rgba(61,43,31,0.14)";

const ChatWindow = ({
  sessionId,
  onAgentEvent,
  onNewMessage,
  onReset,
  messages,
  activeProfile,
}) => {
  const t = useT();
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [language, setLanguage] = useState("Auto-detect");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const stopRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || sending) return;

    setSending(true);
    setInput("");

    // Add user message immediately
    onNewMessage({ role: "user", text, id: Date.now() });

    // Notify pipeline that we're starting
    onAgentEvent({ event: "stream_start" });

    const cleanup = streamChat({
      sessionId,
      message: text,
      languageHint: language === "Auto-detect" ? null : language,
      profileId: activeProfile?.profile_id || null,
      onEvent: (data) => {
        onAgentEvent(data);
        if (data.event === "final_response") {
          onNewMessage({
            role: "assistant",
            text: data.response || "",
            confidence: data.confidence,
            turnNumber: data.turn_number,
            detectedLanguage: data.detected_language || "English",
            fraudFlags: data.fraud_flags || [],
            clarification: data.clarification_needed,
            nextSteps: data.next_steps || [],
            relatedSchemes: data.related_schemes || [],
            id: Date.now(),
          });
          setSending(false);
        } else if (data.event === "error") {
          onNewMessage({
            role: "assistant",
            text: `Error: ${data.error}`,
            confidence: 0,
            id: Date.now(),
          });
          setSending(false);
        }
      },
      onDone: () => setSending(false),
      onError: (err) => {
        console.error("Stream error", err);
        onNewMessage({
          role: "assistant",
          text: `Connection error: ${err.message}`,
          confidence: 0,
          id: Date.now(),
        });
        setSending(false);
      },
    });
    stopRef.current = cleanup;
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: `1px solid ${BORDER}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "rgba(255,255,255,0.4)",
          backdropFilter: "blur(10px)",
          flexShrink: 0,
        }}
      >
        <div>
          <div
            style={{
              fontSize: "17px",
              fontWeight: 700,
              color: "var(--text-primary)",
            }}
          >
            {t("Financial Assistant")}
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            {t("Rural India · Multi-Agent AI")}
            {activeProfile && (
              <span style={{ color: "var(--green)", marginLeft: "6px" }}>
                · {activeProfile.name} (
                {activeProfile.literacy_level || "unassessed"})
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* Language selector */}
          <select
            id="language-selector"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{
              background: "rgba(255,255,255,0.5)",
              border: `1px solid ${BORDER}`,
              color: "var(--text-secondary)",
              borderRadius: "99px",
              padding: "8px 14px",
              fontSize: "13px",
              cursor: "pointer",
              outline: "none",
              fontFamily: "var(--font-sans)",
            }}
          >
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          {/* Reset button */}
          <button
            id="reset-session-btn"
            onClick={onReset}
            title={t("Reset session")}
            style={{
              background: "var(--red-dim)",
              border: "1px solid rgba(220,38,38,0.3)",
              color: "var(--red)",
              borderRadius: "99px",
              padding: "8px 16px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s",
              fontFamily: "var(--font-sans)",
            }}
          >
            {t("Reset")}
          </button>
        </div>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "12px",
              color: "var(--text-muted)",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "52px",
                filter: "drop-shadow(0 0 20px rgba(184,92,56,0.35))",
              }}
            >
              🌾
            </div>
            <div
              style={{
                fontSize: "20px",
                fontWeight: 700,
                color: "var(--text-primary)",
              }}
            >
              {t("Welcome to Sahayak AI")}
            </div>
            <div
              style={{
                fontSize: "15px",
                maxWidth: "360px",
                lineHeight: 1.7,
                color: "var(--text-secondary)",
              }}
            >
              {t(
                "Ask me about government schemes, farming subsidies, loan options, or financial help in any Indian language.",
              )}
            </div>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
                justifyContent: "center",
                marginTop: "12px",
              }}
            >
              {[
                "PM Kisan ke liye apply kaise karein?",
                "What is MSP for wheat today?",
                "Kisan Credit Card documents?",
                "PMFBY insurance kaise milti hai?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setInput(q);
                    inputRef.current?.focus();
                  }}
                  style={{
                    background: "rgba(255,255,255,0.5)",
                    border: `1px solid ${BORDER}`,
                    borderRadius: "99px",
                    padding: "9px 16px",
                    fontSize: "13px",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    transition: "all 0.2s",
                    fontFamily: "var(--font-sans)",
                  }}
                  onMouseEnter={(e) =>
                    (e.target.style.borderColor = "var(--accent-primary)")
                  }
                  onMouseLeave={(e) => (e.target.style.borderColor = BORDER)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} sessionId={sessionId} />
        ))}
        {sending && (
          <div
            className="animate-fade-in"
            style={{
              display: "flex",
              gap: "8px",
              alignItems: "center",
              color: "var(--text-muted)",
              fontSize: "13px",
              padding: "4px 0",
            }}
          >
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "var(--accent-primary)",
                animation: "pulse-ring 1s infinite",
              }}
            />
            {t("Agents working…")}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: "14px 18px",
          borderTop: `1px solid ${BORDER}`,
          background: "rgba(255,255,255,0.45)",
          backdropFilter: "blur(10px)",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: "10px",
            alignItems: "flex-end",
            background: "rgba(255,255,255,0.55)",
            border: `1px solid ${sending ? "var(--accent-primary)" : BORDER}`,
            borderRadius: "20px",
            padding: "10px 14px",
            transition: "border-color 0.2s",
          }}
        >
          <textarea
            ref={inputRef}
            id="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("Ask in any language")}
            disabled={sending}
            rows={1}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--text-primary)",
              fontSize: "15px",
              resize: "none",
              fontFamily: "var(--font-sans)",
              lineHeight: 1.5,
              maxHeight: "100px",
              overflow: "auto",
            }}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height =
                Math.min(e.target.scrollHeight, 100) + "px";
            }}
          />
          <button
            id="send-btn"
            onClick={handleSend}
            disabled={!input.trim() || sending}
            style={{
              background:
                !input.trim() || sending
                  ? "var(--agent-pending)"
                  : "linear-gradient(135deg, var(--accent-primary), #9a4a2c)",
              border: "none",
              borderRadius: "99px",
              padding: "9px 20px",
              cursor: !input.trim() || sending ? "default" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "14px",
              fontWeight: 600,
              color: "#fff",
              flexShrink: 0,
              fontFamily: "var(--font-sans)",
              transition: "all 0.2s",
              boxShadow:
                !input.trim() || sending
                  ? "none"
                  : "0 0 12px rgba(184,92,56,0.4)",
            }}
          >
            {sending ? t("Sending…") : t("Send")}
          </button>
        </div>
        <div
          style={{
            fontSize: "11px",
            color: "var(--text-muted)",
            marginTop: "7px",
            textAlign: "center",
          }}
        >
          Session:{" "}
          <span
            style={{
              fontFamily: "var(--font-mono)",
              color: "var(--text-muted)",
            }}
          >
            {sessionId.slice(0, 8)}…
          </span>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
