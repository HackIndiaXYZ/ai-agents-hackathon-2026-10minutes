// components/AgentPipeline.jsx
// Live visualization of the agent graph execution.
// Each agent is a card that animates through: pending → running → done/error.

import React from "react";

const BORDER = "rgba(61,43,31,0.14)";

const AGENT_ORDER = [
  { id: "language",       label: "Language",      desc: "Language detection" },
  { id: "context",        label: "Context",       desc: "User profile extraction" },
  { id: "supervisor",     label: "Supervisor",    desc: "Routing decision" },
  { id: "clarification",  label: "Clarification", desc: "Query clarification" },
  { id: "decomposition",  label: "Decompose",     desc: "Sub-query breakdown" },
  { id: "web_search",     label: "Web Search",    desc: "Live data retrieval" },
  { id: "reasoning",      label: "Reasoning",     desc: "Evidence synthesis" },
  { id: "recommendation", label: "Recommend",     desc: "Next steps" },
  { id: "fraud_safety",   label: "Safety",        desc: "Fraud & safety check" },
  { id: "formatter",      label: "Formatter",     desc: "Response assembly" },
  { id: "feedback",       label: "Feedback",      desc: "Session logging" },
];

const STATUS_STYLES = {
  pending: {
    bg: "rgba(255,255,255,0.4)",
    border: "rgba(61,43,31,0.14)",
    dot: "rgba(61,43,31,0.35)",
    label: "PENDING",
    labelColor: "rgba(61,43,31,0.5)",
  },
  running: {
    bg: "rgba(184,92,56,0.12)",
    border: "rgba(184,92,56,0.5)",
    dot: "#B85C38",
    label: "RUNNING",
    labelColor: "#B85C38",
    pulse: true,
  },
  done: {
    bg: "rgba(16,133,89,0.12)",
    border: "rgba(16,133,89,0.45)",
    dot: "#0f8a57",
    label: "DONE",
    labelColor: "#0f8a57",
  },
  error: {
    bg: "rgba(220,38,38,0.1)",
    border: "rgba(220,38,38,0.45)",
    dot: "#dc2626",
    label: "ERROR",
    labelColor: "#dc2626",
  },
  skipped: {
    bg: "rgba(255,255,255,0.25)",
    border: "rgba(61,43,31,0.1)",
    dot: "rgba(61,43,31,0.25)",
    label: "SKIP",
    labelColor: "rgba(61,43,31,0.4)",
  },
};

const AgentCard = ({ agent, status, latencyMs }) => {
  const s = STATUS_STYLES[status] || STATUS_STYLES.pending;
  return (
    <div style={{
      background: s.bg,
      border: `1px solid ${s.border}`,
      borderRadius: "16px",
      padding: "12px 14px",
      display: "flex", alignItems: "center", gap: "11px",
      transition: "all 0.3s ease",
      boxShadow: s.pulse ? "0 0 14px rgba(184,92,56,0.25)" : "none",
      animation: s.pulse ? "pulse-ring 1.2s infinite" : "none",
      position: "relative", overflow: "hidden",
    }}>
      <div style={{
        width: "10px", height: "10px", borderRadius: "50%", flexShrink: 0,
        background: s.dot,
        boxShadow: s.pulse ? `0 0 8px ${s.dot}` : "none",
      }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "3px" }}>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
            {agent.label}
          </span>
          <span style={{
            fontSize: "10px", fontWeight: 700, letterSpacing: "0.5px",
            color: s.labelColor, background: `${s.dot}1f`,
            border: `1px solid ${s.border}`, padding: "1px 8px", borderRadius: "99px",
          }}>
            {s.label}
          </span>
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {agent.desc}
        </div>
      </div>
      {latencyMs != null && status === "done" && (
        <span style={{
          fontSize: "11px", color: "var(--green)", fontFamily: "var(--font-mono)",
          flexShrink: 0,
        }}>
          {latencyMs}ms
        </span>
      )}
      {s.pulse && (
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0, height: "2px",
          background: "linear-gradient(90deg, transparent, #B85C38, transparent)",
          backgroundSize: "200% 100%",
          animation: "shimmer 1.2s linear infinite",
        }} />
      )}
    </div>
  );
};

const AgentPipeline = ({ agentStates }) => {
  return (
    <div style={{ padding: "18px" }}>
      <div style={{
        marginBottom: "18px", paddingBottom: "14px",
        borderBottom: `1px solid ${BORDER}`,
      }}>
        <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>
          Agent Pipeline
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
          Live execution trace
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {AGENT_ORDER.map((agent) => {
          const state = agentStates[agent.id] || {};
          return (
            <AgentCard
              key={agent.id}
              agent={agent}
              status={state.status || "pending"}
              latencyMs={state.latencyMs}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div style={{
        display: "flex", flexWrap: "wrap", gap: "10px", marginTop: "18px",
        paddingTop: "14px", borderTop: `1px solid ${BORDER}`,
      }}>
        {Object.entries(STATUS_STYLES).map(([key, val]) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: val.dot }} />
            <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>{key}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentPipeline;
