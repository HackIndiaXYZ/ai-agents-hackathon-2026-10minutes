// components/KnowledgeGraph.jsx — SVG knowledge graph visualisation

import React, { useState } from "react";

const DOMAINS = [
  { key: "Banking & Digital Payments", short: "Banking", icon: "🏦", color: "#3b82f6" },
  { key: "Government Schemes",         short: "Govt Schemes", icon: "🏛️", color: "#10b981" },
  { key: "Fraud & Cyber Safety",       short: "Fraud Safety", icon: "🛡️", color: "#ef4444" },
  { key: "Savings & Insurance",        short: "Savings", icon: "💰", color: "#f59e0b" },
  { key: "Credit & Borrowing",         short: "Credit", icon: "📋", color: "#a855f7" },
];

const LEVEL_LABELS = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" };
const LEVEL_COLORS = { beginner: "#ef4444", intermediate: "#f59e0b", advanced: "#10b981" };

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// Pentagon layout (5 nodes evenly spaced on a circle)
function pentagonPoints(cx, cy, r) {
  return DOMAINS.map((_, i) => {
    const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });
}

function RadarPolygon({ points, scores, colors }) {
  // Filled polygon sized by score
  const scaled = points.map((p, i) => {
    const cx = 200, cy = 200;
    const score = scores[i] ?? 0;
    return {
      x: cx + (p.x - cx) * score,
      y: cy + (p.y - cy) * score,
    };
  });
  const d = scaled.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
  return (
    <path
      d={d}
      fill="rgba(99,102,241,0.18)"
      stroke="rgba(99,102,241,0.6)"
      strokeWidth="2"
      strokeLinejoin="round"
    />
  );
}

function GridLines({ points }) {
  const cx = 200, cy = 200;
  const levels = [0.25, 0.5, 0.75, 1.0];
  return (
    <>
      {levels.map((lvl) => {
        const scaled = points.map((p) => ({
          x: cx + (p.x - cx) * lvl,
          y: cy + (p.y - cy) * lvl,
        }));
        const d = scaled.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
        return (
          <path key={lvl} d={d} fill="none" stroke="rgba(99,120,180,0.12)" strokeWidth="1" />
        );
      })}
      {/* Spokes */}
      {points.map((p, i) => (
        <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(99,120,180,0.15)" strokeWidth="1" />
      ))}
    </>
  );
}

function DomainNode({ domain, point, score, isSelected, onClick }) {
  const radius = 30;
  const { color, icon, short } = domain;
  const textY = point.y > 200 ? point.y + radius + 16 : point.y - radius - 6;

  return (
    <g onClick={onClick} style={{ cursor: "pointer" }}>
      {/* Outer ring (score indicator) */}
      <circle
        cx={point.x} cy={point.y} r={radius + 4}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeOpacity={0.3}
        strokeDasharray={`${(score * 2 * Math.PI * (radius + 4)).toFixed(1)} 999`}
        strokeLinecap="round"
        transform={`rotate(-90 ${point.x} ${point.y})`}
      />
      {/* Inner circle */}
      <circle
        cx={point.x} cy={point.y} r={radius}
        fill={hexToRgba(color, isSelected ? 0.25 : 0.12)}
        stroke={color}
        strokeWidth={isSelected ? 2.5 : 1.5}
      />
      {/* Score arc fill */}
      <circle
        cx={point.x} cy={point.y} r={radius - 6}
        fill={hexToRgba(color, score * 0.35)}
      />
      {/* Icon */}
      <text x={point.x} y={point.y - 4} textAnchor="middle" fontSize="14" dominantBaseline="middle">
        {icon}
      </text>
      {/* Score % */}
      <text x={point.x} y={point.y + 12} textAnchor="middle" fontSize="10" fill={color} fontWeight="700">
        {Math.round(score * 100)}%
      </text>
      {/* Label below/above node */}
      <text
        x={point.x}
        y={textY}
        textAnchor="middle"
        fontSize="11"
        fill={isSelected ? color : "rgba(232,234,246,0.7)"}
        fontWeight={isSelected ? "700" : "400"}
      >
        {short}
      </text>
    </g>
  );
}

function ConceptList({ domainData, color }) {
  const concepts = Object.entries(domainData?.concepts || {});
  if (!concepts.length) return <div style={{ color: "var(--text-muted)", fontSize: "12px" }}>No concepts assessed yet.</div>;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
      {concepts.map(([concept, info]) => (
        <div key={concept} style={{
          padding: "3px 10px",
          borderRadius: "99px",
          fontSize: "11px",
          fontWeight: 500,
          background: info.known ? hexToRgba(color, 0.15) : "var(--bg-card)",
          border: `1px solid ${info.known ? color : "var(--border-subtle)"}`,
          color: info.known ? color : "var(--text-muted)",
        }}>
          {concept}
          <span style={{ opacity: 0.6, marginLeft: "4px" }}>
            {Math.round((info.confidence || 0) * 100)}%
          </span>
        </div>
      ))}
    </div>
  );
}

export default function KnowledgeGraph({ kg, profile }) {
  const [selectedDomain, setSelectedDomain] = useState(null);

  if (!kg) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-muted)" }}>
        <div style={{ fontSize: "32px", marginBottom: "12px" }}>📊</div>
        <div>Complete the assessment to see your knowledge graph.</div>
      </div>
    );
  }

  const points = pentagonPoints(200, 200, 140);
  const scores = DOMAINS.map((d) => kg.domains?.[d.key]?.score ?? 0);
  const overallLevel = kg.literacy_level || "beginner";
  const selectedDomainMeta = DOMAINS.find((d) => d.key === selectedDomain);
  const selectedDomainData = selectedDomain ? kg.domains?.[selectedDomain] : null;

  return (
    <div style={{ maxWidth: "560px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <div style={{ fontSize: "18px", fontWeight: 700, marginBottom: "4px" }}>
          Your Financial Knowledge Graph
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
            {profile?.name}
          </span>
          <span style={{
            padding: "2px 10px",
            background: hexToRgba(LEVEL_COLORS[overallLevel], 0.15),
            border: `1px solid ${LEVEL_COLORS[overallLevel]}`,
            borderRadius: "99px",
            fontSize: "11px",
            color: LEVEL_COLORS[overallLevel],
            fontWeight: 700,
          }}>
            {LEVEL_LABELS[overallLevel]} — {Math.round((kg.overall_score || 0) * 100)}% overall
          </span>
          {kg.chat_interactions > 0 && (
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              +{kg.chat_interactions} chat interactions
            </span>
          )}
        </div>
      </div>

      {/* Radar chart */}
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)", padding: "16px",
        marginBottom: "16px",
      }}>
        <svg viewBox="0 0 400 400" style={{ width: "100%", maxHeight: "360px" }}>
          <GridLines points={points} />
          <RadarPolygon points={points} scores={scores} colors={DOMAINS.map((d) => d.color)} />
          {DOMAINS.map((domain, i) => (
            <DomainNode
              key={domain.key}
              domain={domain}
              point={points[i]}
              score={scores[i]}
              isSelected={selectedDomain === domain.key}
              onClick={() => setSelectedDomain(selectedDomain === domain.key ? null : domain.key)}
            />
          ))}
          {/* Centre label */}
          <text x="200" y="194" textAnchor="middle" fontSize="11" fill="rgba(232,234,246,0.4)">
            Knowledge
          </text>
          <text x="200" y="208" textAnchor="middle" fontSize="11" fill="rgba(232,234,246,0.4)">
            Graph
          </text>
        </svg>
        <div style={{ textAlign: "center", fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
          Click a domain node to explore its concepts
        </div>
      </div>

      {/* Domain detail panel */}
      {selectedDomain && selectedDomainData && selectedDomainMeta && (
        <div className="animate-fade-in" style={{
          padding: "16px 20px",
          background: "var(--bg-card)",
          border: `1px solid ${selectedDomainMeta.color}`,
          borderRadius: "var(--radius-lg)",
          marginBottom: "16px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
            <span style={{ fontSize: "20px" }}>{selectedDomainMeta.icon}</span>
            <div>
              <div style={{ fontSize: "14px", fontWeight: 700, color: selectedDomainMeta.color }}>
                {selectedDomain}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                {selectedDomainData.questions_asked || 0} questions assessed ·{" "}
                <span style={{ color: LEVEL_COLORS[selectedDomainData.level || "beginner"] }}>
                  {LEVEL_LABELS[selectedDomainData.level || "beginner"]}
                </span>
                {" "}· {Math.round((selectedDomainData.score || 0) * 100)}% confidence
              </div>
            </div>
            {/* Score bar */}
            <div style={{ marginLeft: "auto", textAlign: "right" }}>
              <div style={{
                width: "80px", height: "6px", borderRadius: "99px",
                background: "var(--border-subtle)", overflow: "hidden",
              }}>
                <div style={{
                  height: "100%",
                  width: `${(selectedDomainData.score || 0) * 100}%`,
                  background: selectedDomainMeta.color,
                  borderRadius: "99px",
                  transition: "width 0.5s ease",
                }} />
              </div>
            </div>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "6px" }}>
            Concepts assessed:
          </div>
          <ConceptList domainData={selectedDomainData} color={selectedDomainMeta.color} />
        </div>
      )}

      {/* Domain score cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
        {DOMAINS.map((domain, i) => {
          const data = kg.domains?.[domain.key];
          const score = data?.score ?? 0;
          const level = data?.level || "beginner";
          const conceptCount = Object.keys(data?.concepts || {}).length;

          return (
            <div
              key={domain.key}
              onClick={() => setSelectedDomain(selectedDomain === domain.key ? null : domain.key)}
              style={{
                padding: "12px 14px",
                background: selectedDomain === domain.key
                  ? hexToRgba(domain.color, 0.1)
                  : "var(--bg-card)",
                border: `1px solid ${selectedDomain === domain.key ? domain.color : "var(--border-subtle)"}`,
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                <span style={{ fontSize: "14px" }}>{domain.icon}</span>
                <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>
                  {domain.short}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{
                  flex: 1, height: "4px", borderRadius: "99px",
                  background: "var(--border-subtle)", overflow: "hidden",
                }}>
                  <div style={{
                    height: "100%", width: `${score * 100}%`,
                    background: domain.color, borderRadius: "99px",
                    transition: "width 0.5s ease",
                  }} />
                </div>
                <span style={{ fontSize: "11px", color: domain.color, fontWeight: 700, minWidth: "30px" }}>
                  {Math.round(score * 100)}%
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px" }}>
                <span style={{ fontSize: "10px", color: LEVEL_COLORS[level] }}>
                  {LEVEL_LABELS[level]}
                </span>
                <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                  {conceptCount} concepts
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Last updated */}
      {kg.last_updated && (
        <div style={{ marginTop: "12px", fontSize: "10px", color: "var(--text-muted)", textAlign: "right" }}>
          Last updated: {new Date(kg.last_updated).toLocaleDateString()}
        </div>
      )}
    </div>
  );
}
