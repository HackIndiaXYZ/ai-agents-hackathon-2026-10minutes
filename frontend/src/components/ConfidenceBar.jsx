// components/ConfidenceBar.jsx
import React from "react";

const ConfidenceBar = ({ score }) => {
  const pct = Math.round((score || 0) * 100);
  const color = pct >= 80 ? "#10b981" : pct >= 60 ? "#f59e0b" : "#ef4444";
  const label = pct >= 80 ? "High" : pct >= 60 ? "Medium" : "Low";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px" }}>
      <div style={{
        flex: 1, height: "4px", borderRadius: "99px",
        background: "rgba(255,255,255,0.08)",
        overflow: "hidden",
      }}>
        <div style={{
          height: "100%", width: `${pct}%`,
          background: `linear-gradient(90deg, ${color}88, ${color})`,
          borderRadius: "99px",
          transition: "width 0.6s cubic-bezier(0.4,0,0.2,1)",
          boxShadow: `0 0 8px ${color}66`,
        }} />
      </div>
      <span style={{
        fontSize: "11px", fontWeight: 600, color,
        background: `${color}18`, border: `1px solid ${color}33`,
        padding: "1px 7px", borderRadius: "99px", whiteSpace: "nowrap",
      }}>
        {pct}% {label}
      </span>
    </div>
  );
};

export default ConfidenceBar;
