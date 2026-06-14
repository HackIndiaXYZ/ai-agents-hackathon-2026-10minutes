// components/MessageBubble.jsx
import React, { useState } from "react";
import ConfidenceBar from "./ConfidenceBar";
import FeedbackButtons from "./FeedbackButtons";

const LANG_FLAGS = {
  Hindi: "🇮🇳", Bengali: "🇧🇩", Marathi: "🇮🇳", Tamil: "🇮🇳",
  Telugu: "🇮🇳", Gujarati: "🇮🇳", Kannada: "🇮🇳",
  Malayalam: "🇮🇳", Punjabi: "🇮🇳", Urdu: "🇵🇰", English: "🌐",
};

// ─── Next Steps Panel ─────────────────────────────────────────────────────────

const NextStepsPanel = ({ nextSteps = [], relatedSchemes = [] }) => {
  const [open, setOpen] = useState(true);

  if (!nextSteps.length && !relatedSchemes.length) return null;

  return (
    <div style={{
      marginTop: "10px",
      border: "1px solid rgba(99,102,241,0.25)",
      borderRadius: "12px",
      overflow: "hidden",
      background: "rgba(99,102,241,0.04)",
    }}>
      {/* Header toggle */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "9px 14px", background: "transparent", border: "none",
          cursor: "pointer", color: "var(--text-secondary)", fontSize: "12px", fontWeight: 700,
          letterSpacing: "0.04em", textTransform: "uppercase",
        }}
      >
        <span>📋 Next Steps{nextSteps.length ? ` (${nextSteps.length})` : ""}</span>
        <span style={{ fontSize: "10px", opacity: 0.7 }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div style={{ padding: "0 14px 12px" }}>
          {/* Steps */}
          {nextSteps.map((step, i) => (
            <div key={i} style={{
              display: "flex", gap: "10px", marginBottom: "10px", alignItems: "flex-start",
            }}>
              {/* Step number badge */}
              <div style={{
                width: "22px", height: "22px", borderRadius: "50%", flexShrink: 0,
                background: "linear-gradient(135deg, var(--accent-primary), #4f46e5)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "11px", fontWeight: 700, color: "#fff", marginTop: "1px",
              }}>
                {step.step_number || i + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "13px", color: "var(--text-primary)", fontWeight: 600, lineHeight: 1.4 }}>
                  {step.action}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "4px" }}>
                  {step.where && (
                    <span style={{
                      fontSize: "10px", padding: "2px 7px", borderRadius: "99px",
                      background: "var(--bg-input)", color: "var(--text-muted)",
                      border: "1px solid var(--border-subtle)",
                    }}>📍 {step.where}</span>
                  )}
                  {step.estimated_time && (
                    <span style={{
                      fontSize: "10px", padding: "2px 7px", borderRadius: "99px",
                      background: "var(--bg-input)", color: "var(--text-muted)",
                      border: "1px solid var(--border-subtle)",
                    }}>⏱ {step.estimated_time}</span>
                  )}
                  {(step.required_documents || []).slice(0, 3).map((doc, di) => (
                    <span key={di} style={{
                      fontSize: "10px", padding: "2px 7px", borderRadius: "99px",
                      background: "rgba(245,158,11,0.1)", color: "var(--amber)",
                      border: "1px solid rgba(245,158,11,0.25)",
                    }}>📄 {doc}</span>
                  ))}
                </div>
              </div>
            </div>
          ))}

          {/* Related schemes */}
          {relatedSchemes.length > 0 && (
            <div style={{ marginTop: "8px", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Related Schemes
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {relatedSchemes.map((scheme, i) => (
                  <div key={i} title={scheme.relevance_reason || ""} style={{
                    fontSize: "11px", padding: "3px 10px", borderRadius: "99px",
                    background: "rgba(16,185,129,0.1)", color: "var(--green)",
                    border: "1px solid rgba(16,185,129,0.25)", cursor: "default",
                    fontWeight: 600,
                  }}>
                    🏛 {scheme.scheme_name}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ─── Main MessageBubble ───────────────────────────────────────────────────────

const MessageBubble = ({ message, sessionId }) => {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="animate-slide-right" style={{
        display: "flex", justifyContent: "flex-end", marginBottom: "12px",
      }}>
        <div style={{
          maxWidth: "70%", background: "linear-gradient(135deg, var(--accent-primary), #4f46e5)",
          padding: "10px 14px", borderRadius: "16px 16px 4px 16px",
          color: "#fff", fontSize: "14px", lineHeight: "1.5",
          boxShadow: "0 2px 12px rgba(99,102,241,0.3)",
        }}>
          {message.text}
        </div>
      </div>
    );
  }

  // Assistant message
  const {
    text, confidence, turnNumber, detectedLanguage,
    fraudFlags = [], clarification,
    nextSteps = [], relatedSchemes = [],
  } = message;
  const flag = LANG_FLAGS[detectedLanguage] || "🌐";
  const hasFraud = fraudFlags.length > 0;

  return (
    <div className="animate-slide-left" style={{
      display: "flex", gap: "10px", marginBottom: "16px", alignItems: "flex-start",
    }}>
      {/* Avatar */}
      <div style={{
        width: "32px", height: "32px", borderRadius: "50%", flexShrink: 0,
        background: "linear-gradient(135deg, var(--accent-primary), #6d28d9)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "14px", boxShadow: "0 0 12px rgba(99,102,241,0.4)",
      }}>
        🤖
      </div>

      <div style={{ flex: 1, maxWidth: "75%" }}>
        {/* Language badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "5px" }}>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{flag} {detectedLanguage}</span>
          {clarification && (
            <span style={{
              fontSize: "10px", padding: "1px 7px", borderRadius: "99px",
              background: "var(--amber-dim)", color: "var(--amber)",
              border: "1px solid rgba(245,158,11,0.3)", fontWeight: 600,
            }}>CLARIFYING</span>
          )}
          {hasFraud && (
            <span style={{
              fontSize: "10px", padding: "1px 7px", borderRadius: "99px",
              background: "var(--red-dim)", color: "var(--red)",
              border: "1px solid rgba(239,68,68,0.3)", fontWeight: 600,
            }}>⚠ SAFETY FILTER</span>
          )}
        </div>

        {/* Answer bubble */}
        <div style={{
          background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
          padding: "12px 14px", borderRadius: "4px 16px 16px 16px",
          fontSize: "14px", lineHeight: "1.7", color: "var(--text-primary)",
          boxShadow: "var(--shadow-card)", whiteSpace: "pre-wrap",
        }}>
          {text}
        </div>

        {/* Next Steps panel — rendered below the answer bubble */}
        {!clarification && (
          <NextStepsPanel nextSteps={nextSteps} relatedSchemes={relatedSchemes} />
        )}

        {/* Confidence */}
        {typeof confidence === "number" && !clarification && (
          <ConfidenceBar score={confidence} />
        )}

        {/* Feedback */}
        {!clarification && turnNumber && (
          <FeedbackButtons sessionId={sessionId} turnNumber={turnNumber} />
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
