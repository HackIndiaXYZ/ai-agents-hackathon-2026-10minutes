// components/LiteracyProgress.jsx — Literacy Progress Dashboard

import React, { useState, useEffect, useCallback } from "react";
import { getLiteracyProgress } from "../api/client";
import { useT, useLang } from "../i18n";
import {
  Panel, SectionTitle, LoadingState, ErrorState, EmptyState, Chip,
} from "./featureKit";

const DOMAIN_META = {
  "Banking & Digital Payments": { short: "Banking", icon: "🏦", color: "#3b82f6" },
  "Government Schemes":         { short: "Govt Schemes", icon: "🏛️", color: "#10b981" },
  "Fraud & Cyber Safety":       { short: "Fraud Safety", icon: "🛡️", color: "#ef4444" },
  "Savings & Insurance":        { short: "Savings", icon: "💰", color: "#f59e0b" },
  "Credit & Borrowing":         { short: "Credit", icon: "📋", color: "#a855f7" },
};
const LEVEL_COLORS = { beginner: "#ef4444", intermediate: "#f59e0b", advanced: "#10b981" };

function Sparkline({ timeline }) {
  if (!timeline || timeline.length < 2) return null;
  const w = 280, h = 70, pad = 6;
  const xs = timeline.map((_, i) => pad + (i * (w - 2 * pad)) / (timeline.length - 1));
  const ys = timeline.map((t) => h - pad - ((t.overall || 0) / 100) * (h - 2 * pad));
  const line = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(" ");
  const area = `${line} L ${xs[xs.length - 1].toFixed(1)} ${h - pad} L ${xs[0].toFixed(1)} ${h - pad} Z`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: "70px" }}>
      <defs>
        <linearGradient id="sparkfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(99,102,241,0.35)" />
          <stop offset="100%" stopColor="rgba(99,102,241,0)" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#sparkfill)" />
      <path d={line} fill="none" stroke="var(--accent-primary)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {xs.map((x, i) => (
        <circle key={i} cx={x} cy={ys[i]} r={i === xs.length - 1 ? 3.5 : 2}
          fill={i === xs.length - 1 ? "var(--accent-secondary)" : "var(--accent-primary)"} />
      ))}
    </svg>
  );
}

function DomainBar({ domain, percent, isWeak }) {
  const t = useT();
  const meta = DOMAIN_META[domain] || { short: domain, icon: "•", color: "#6366f1" };
  return (
    <div style={{ marginBottom: "11px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
        <span style={{ fontSize: "13px" }}>{meta.icon}</span>
        <span style={{ fontSize: "12px", color: "var(--text-primary)", fontWeight: 500 }}>{t(meta.short)}</span>
        {isWeak && <Chip color="var(--red)">{t("needs work")}</Chip>}
        <span style={{ marginLeft: "auto", fontSize: "12px", fontWeight: 700, color: meta.color }}>{percent}%</span>
      </div>
      <div style={{ height: "6px", borderRadius: "99px", background: "var(--border-subtle)", overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${percent}%`, background: meta.color, borderRadius: "99px", transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

function NextStepCard({ step }) {
  const t = useT();
  const meta = DOMAIN_META[step.domain] || { color: "#6366f1", icon: "💡" };
  return (
    <div style={{
      padding: "12px 14px", marginBottom: "9px", background: "var(--bg-input)",
      borderRadius: "var(--radius-md)", borderLeft: `3px solid ${meta.color}`,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "4px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "13px" }}>{meta.icon}</span>
        <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>{step.title}</span>
        <Chip color={meta.color}>{step.difficulty}</Chip>
      </div>
      {step.why && <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px", lineHeight: 1.5 }}>{step.why}</div>}
      {step.action && (
        <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
          <strong style={{ color: meta.color }}>{t("Do this:")} </strong>{step.action}
        </div>
      )}
    </div>
  );
}

export default function LiteracyProgress({ profile }) {
  const t = useT();
  const { lang } = useLang();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!profile?.profile_id) return;
    setLoading(true); setError("");
    try {
      setData(await getLiteracyProgress(profile.profile_id, lang));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [profile, lang]);

  useEffect(() => { load(); }, [load]);

  if (!profile?.profile_id) {
    return <Panel><EmptyState icon="🧠" title={t("Complete your assessment first")} hint={t("Your progress dashboard appears once you've finished the financial knowledge assessment.")} /></Panel>;
  }

  const level = data?.literacy_level || "beginner";
  const improved = data?.improvement_since_start || 0;

  return (
    <Panel>
      <SectionTitle
        icon="📈"
        title={t("Your Learning Progress")}
        subtitle={`${t("Tracking financial literacy over time for")} ${profile.name}`}
        right={
          <button onClick={load} disabled={loading} style={{
            padding: "6px 12px", background: "var(--bg-card-hover)", border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)", color: "var(--text-secondary)", fontSize: "11px",
            cursor: loading ? "default" : "pointer",
          }}>↻</button>
        }
      />

      {loading && !data && <LoadingState message={t("Loading your progress…")} rows={3} />}
      {error && <ErrorState message={error} onRetry={load} />}

      {data && data.has_data && (
        <>
          {/* Top stats */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px", marginBottom: "16px" }}>
            <div style={statBox}>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "var(--accent-secondary)" }}>{data.overall_score}%</div>
              <div style={statLabel}>{t("Overall")}</div>
            </div>
            <div style={statBox}>
              <div style={{ fontSize: "16px", fontWeight: 700, color: LEVEL_COLORS[level], textTransform: "capitalize", marginTop: "4px" }}>{t(level)}</div>
              <div style={statLabel}>{t("Level")}</div>
            </div>
            <div style={statBox}>
              <div style={{ fontSize: "24px", fontWeight: 700, color: improved >= 0 ? "var(--green)" : "var(--red)" }}>
                {improved >= 0 ? "+" : ""}{improved}
              </div>
              <div style={statLabel}>{t("Since start")}</div>
            </div>
          </div>

          {/* Timeline */}
          {data.timeline?.length >= 2 && (
            <div style={{ marginBottom: "16px" }}>
              <div style={miniLabel}>{t("OVERALL SCORE OVER TIME")}</div>
              <Sparkline timeline={data.timeline} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-muted)" }}>
                <span>{data.timeline.length} {t("checkpoints")}</span>
                <span>{t("now:")} {data.timeline[data.timeline.length - 1].overall}%</span>
              </div>
            </div>
          )}

          {/* Domain breakdown */}
          <div style={{ marginBottom: "16px" }}>
            <div style={miniLabel}>{t("BY DOMAIN")}</div>
            {Object.entries(data.current_domains).map(([d, p]) => (
              <DomainBar key={d} domain={d} percent={p} isWeak={data.weakest_domains.includes(d)} />
            ))}
          </div>

          {/* Next steps */}
          {data.next_steps?.length > 0 && (
            <div>
              <div style={miniLabel}>📚 {t("WHAT TO LEARN NEXT")}</div>
              {data.next_steps.map((s, i) => <NextStepCard key={i} step={s} />)}
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

const statBox = {
  padding: "12px 8px", textAlign: "center", background: "var(--bg-input)",
  borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)",
};
const statLabel = { fontSize: "10px", color: "var(--text-muted)", marginTop: "3px", textTransform: "uppercase", letterSpacing: "0.05em" };
const miniLabel = { fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em" };
