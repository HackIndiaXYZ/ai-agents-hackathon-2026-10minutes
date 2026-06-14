// components/SchemeEligibility.jsx — Scheme Eligibility Engine panel

import React, { useState } from "react";
import { getEligibleSchemes } from "../api/client";
import { useT, useLang } from "../i18n";
import {
  Panel, SectionTitle, LoadingState, ErrorState, EmptyState,
  GroundedBadge, SourceList, Chip, NeedsProfile,
} from "./featureKit";

const LEVEL_COLOR = { Central: "#6366f1", State: "#10b981" };

function MatchRing({ percent }) {
  const color = percent >= 75 ? "var(--green)" : percent >= 55 ? "var(--amber)" : "var(--accent-secondary)";
  const r = 18, c = 2 * Math.PI * r;
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" style={{ flexShrink: 0 }}>
      <circle cx="24" cy="24" r={r} fill="none" stroke="var(--border-subtle)" strokeWidth="4" />
      <circle
        cx="24" cy="24" r={r} fill="none" stroke={color} strokeWidth="4"
        strokeDasharray={`${(percent / 100) * c} ${c}`} strokeLinecap="round"
        transform="rotate(-90 24 24)"
      />
      <text x="24" y="27" textAnchor="middle" fontSize="11" fontWeight="700" fill={color}>
        {percent}%
      </text>
    </svg>
  );
}

function SchemeCard({ scheme, index }) {
  const t = useT();
  const [open, setOpen] = useState(index === 0);
  const levelColor = LEVEL_COLOR[scheme.level] || "var(--accent-secondary)";

  return (
    <div style={{
      border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)",
      overflow: "hidden", marginBottom: "10px", background: "var(--bg-input)",
    }}>
      <div
        onClick={() => setOpen((o) => !o)}
        style={{ display: "flex", alignItems: "center", gap: "12px", padding: "12px 14px", cursor: "pointer" }}
      >
        <MatchRing percent={scheme.match_percent} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "3px" }}>
            {scheme.name}
          </div>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            <Chip color={levelColor} filled>{scheme.level}</Chip>
            {scheme.category && <Chip>{scheme.category}</Chip>}
          </div>
        </div>
        <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>{open ? "▲" : "▼"}</span>
      </div>

      {open && (
        <div className="animate-fade-in" style={{ padding: "0 14px 14px", fontSize: "13px", color: "var(--text-secondary)" }}>
          {scheme.why_eligible && (
            <div style={{
              padding: "8px 12px", background: "rgba(99,102,241,0.07)",
              borderRadius: "var(--radius-sm)", borderLeft: `3px solid ${levelColor}`,
              marginBottom: "10px", lineHeight: 1.5,
            }}>
              <strong style={{ color: "var(--text-primary)" }}>{t("Why you qualify:")} </strong>{scheme.why_eligible}
            </div>
          )}
          {scheme.benefit && (
            <div style={{ marginBottom: "10px" }}>
              <span style={{ color: "var(--text-muted)" }}>{t("Benefit:")} </span>{scheme.benefit}
            </div>
          )}
          {scheme.documents?.length > 0 && (
            <div style={{ marginBottom: "10px" }}>
              <div style={{ color: "var(--text-muted)", marginBottom: "5px" }}>{t("Documents needed:")}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                {scheme.documents.map((d, i) => (
                  <Chip key={i} color="var(--amber)">📄 {d}</Chip>
                ))}
              </div>
            </div>
          )}
          {scheme.where_to_apply && (
            <div style={{ marginBottom: scheme.official_link ? "8px" : 0 }}>
              <span style={{ color: "var(--text-muted)" }}>{t("Where to apply:")} </span>
              📍 {scheme.where_to_apply}
            </div>
          )}
          {scheme.official_link && (
            <a href={scheme.official_link} target="_blank" rel="noreferrer" style={{
              fontSize: "12px", color: "var(--accent-secondary)", textDecoration: "none",
            }}>🔗 {t("Official page")}</a>
          )}
        </div>
      )}
    </div>
  );
}

export default function SchemeEligibility({ profile, onGoToProfile }) {
  const t = useT();
  const { lang } = useLang();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  if (!profile?.profile_id) return <NeedsProfile onGoToProfile={onGoToProfile} />;

  const run = async () => {
    setLoading(true); setError(""); setData(null);
    try {
      setData(await getEligibleSchemes(profile.profile_id, lang));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel>
      <SectionTitle
        icon="🏛️"
        title={t("Schemes You Qualify For")}
        subtitle={`${t("Personalised for")} ${profile.name} · ${profile.occupation} · ${profile.state}`}
        right={data && <GroundedBadge grounded={data.grounded} />}
      />

      {!data && !loading && !error && (
        <>
          <EmptyState
            icon="🎯"
            title={t("Find your government schemes")}
            hint={t("We'll match you against current central and state schemes using live official data, ranked by how well you fit.")}
          />
          <button onClick={run} style={primaryBtn}>{t("Find eligible schemes →")}</button>
        </>
      )}

      {loading && <LoadingState message={t("Matching you against live government scheme data…")} rows={4} />}
      {error && <ErrorState message={error} onRetry={run} />}

      {data && (
        <>
          <div style={{ marginBottom: "14px", fontSize: "12px", color: "var(--text-muted)" }}>
            {t("Found")} <strong style={{ color: "var(--text-primary)" }}>{data.schemes.length}</strong> {t("schemes you likely qualify for, ranked by match.")}
          </div>
          {data.schemes.map((s, i) => <SchemeCard key={i} scheme={s} index={i} />)}
          <SourceList sources={data.sources} />
          <button onClick={run} style={{ ...primaryBtn, marginTop: "14px", background: "var(--bg-card-hover)", color: "var(--text-secondary)" }}>
            ↻ {t("Refresh")}
          </button>
        </>
      )}
    </Panel>
  );
}

const primaryBtn = {
  width: "100%", padding: "11px", marginTop: "8px",
  background: "var(--accent-primary)", border: "none",
  borderRadius: "var(--radius-sm)", color: "#fff",
  fontSize: "13px", fontWeight: 600, cursor: "pointer",
};
