// components/ComplaintGuide.jsx — Guided Complaint Filing panel

import React, { useState } from "react";
import { getComplaintGuide } from "../api/client";
import { useT, useLang } from "../i18n";
import {
  Panel, SectionTitle, LoadingState, ErrorState, EmptyState,
  GroundedBadge, SourceList, Chip,
} from "./featureKit";

const EXAMPLES = [
  "My PM Kisan instalment didn't come this time",
  "Money was debited by a fraudster from my account",
  "Bank refused to open my zero-balance account",
  "My crop insurance claim was rejected",
];

function AuthorityCard({ authority }) {
  const t = useT();
  if (!authority || !Object.keys(authority).length) return null;
  return (
    <div style={{
      padding: "14px 16px", marginBottom: "16px",
      background: "linear-gradient(135deg, rgba(99,102,241,0.1), rgba(124,58,237,0.06))",
      border: "1px solid var(--border-active)", borderRadius: "var(--radius-md)",
    }}>
      <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-secondary)", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {t("Where to complain")}
      </div>
      <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
        {authority.name}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {authority.helpline && (
          <a href={`tel:${authority.helpline}`} style={contactLink}>📞 <strong>{authority.helpline}</strong></a>
        )}
        {authority.portal && (
          <a href={authority.portal} target="_blank" rel="noreferrer" style={contactLink}>🌐 {authority.portal}</a>
        )}
        {authority.email && (
          <a href={`mailto:${authority.email}`} style={contactLink}>✉ {authority.email}</a>
        )}
        {authority.where && (
          <div style={{ ...contactLink, color: "var(--text-secondary)", cursor: "default" }}>📍 {authority.where}</div>
        )}
      </div>
    </div>
  );
}

function Step({ step }) {
  return (
    <div style={{ display: "flex", gap: "12px", marginBottom: "14px" }}>
      <div style={{
        width: "26px", height: "26px", borderRadius: "50%", flexShrink: 0,
        background: "linear-gradient(135deg, var(--accent-primary), #4f46e5)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "12px", fontWeight: 700, color: "#fff",
      }}>{step.step}</div>
      <div style={{ flex: 1, paddingTop: "2px" }}>
        <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.4 }}>{step.action}</div>
        {step.detail && <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "3px", lineHeight: 1.5 }}>{step.detail}</div>}
      </div>
    </div>
  );
}

export default function ComplaintGuide({ profile }) {
  const t = useT();
  const { lang } = useLang();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const run = async (issue) => {
    const q = (issue || input).trim();
    if (!q) return;
    setInput(q);
    setLoading(true); setError(""); setData(null);
    try {
      setData(await getComplaintGuide({
        issue: q,
        profileId: profile?.profile_id || null,
        state: profile?.state || null,
        language: lang,  // follow the interface language
      }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel>
      <SectionTitle
        icon="📢"
        title={t("File a Complaint — Step by Step")}
        subtitle={t("We'll find the right authority and walk you through it")}
        right={data && <GroundedBadge grounded={data.grounded} />}
      />

      <div style={{ marginBottom: "10px" }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t("Describe your problem in your own words…")}
          rows={2}
          style={{
            width: "100%", padding: "11px 14px", background: "var(--bg-input)",
            border: "1px solid var(--border-active)", borderRadius: "var(--radius-sm)",
            color: "var(--text-primary)", fontSize: "13px", outline: "none",
            resize: "vertical", fontFamily: "var(--font-sans)",
          }}
        />
        <button onClick={() => run()} disabled={!input.trim() || loading} style={{
          width: "100%", marginTop: "8px", padding: "11px",
          background: input.trim() && !loading ? "var(--accent-primary)" : "var(--bg-card-hover)",
          border: "none", borderRadius: "var(--radius-sm)", color: "#fff",
          fontSize: "13px", fontWeight: 600, cursor: input.trim() && !loading ? "pointer" : "not-allowed",
        }}>
          {loading ? t("Finding the right authority…") : t("Get my complaint guide →")}
        </button>
      </div>

      {!data && !loading && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "16px" }}>
          {EXAMPLES.map((s) => (
            <button key={s} onClick={() => run(s)} style={{
              background: "var(--bg-input)", border: "1px solid var(--border-subtle)",
              borderRadius: "99px", padding: "5px 12px", fontSize: "11px",
              color: "var(--text-secondary)", cursor: "pointer", textAlign: "left",
            }}>{s}</button>
          ))}
        </div>
      )}

      {!data && !loading && !error && (
        <EmptyState icon="🧭" title={t("Describe what went wrong")} hint={t("We'll identify the correct grievance authority, give you the real portal and helpline, and the exact steps to file — with an escalation path if it isn't resolved.")} />
      )}
      {loading && <LoadingState message={t("Identifying the correct authority and steps…")} rows={4} />}
      {error && <ErrorState message={error} onRetry={() => run()} />}

      {data && (
        <>
          {data.issue_understood && (
            <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px", display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              {data.grievance_type && <Chip color="var(--amber)" filled>{data.grievance_type}</Chip>}
              <span>{data.issue_understood}</span>
            </div>
          )}

          <AuthorityCard authority={data.authority} />

          {data.steps?.length > 0 && (
            <div style={{ marginBottom: "16px" }}>
              <div style={sectionLabel}>{t("STEPS TO FILE")}</div>
              {data.steps.map((s, i) => <Step key={i} step={s} />)}
            </div>
          )}

          {data.documents_to_keep_ready?.length > 0 && (
            <div style={{ marginBottom: "16px" }}>
              <div style={sectionLabel}>{t("KEEP READY")}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                {data.documents_to_keep_ready.map((d, i) => <Chip key={i} color="var(--amber)">📄 {d}</Chip>)}
              </div>
            </div>
          )}

          {data.escalation?.length > 0 && (
            <div style={{ marginBottom: "16px" }}>
              <div style={sectionLabel}>{t("IF NOT RESOLVED — ESCALATE")}</div>
              {data.escalation.map((e, i) => (
                <div key={i} style={{
                  padding: "9px 12px", marginBottom: "6px", background: "var(--bg-input)",
                  borderRadius: "var(--radius-sm)", borderLeft: "3px solid var(--amber)",
                  fontSize: "12px", color: "var(--text-secondary)",
                }}>
                  <strong style={{ color: "var(--text-primary)" }}>{e.authority}</strong>
                  {e.level && <span style={{ color: "var(--text-muted)" }}> · {e.level}</span>}
                  {e.how && <div style={{ marginTop: "2px" }}>{e.how}</div>}
                </div>
              ))}
            </div>
          )}

          {data.expected_timeline && (
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
              ⏱ {t("Expected resolution:")} {data.expected_timeline}
            </div>
          )}

          {data.similar_cases?.length > 0 && (
            <details style={{ marginTop: "8px" }}>
              <summary style={{ fontSize: "11px", color: "var(--text-muted)", cursor: "pointer" }}>
                {data.similar_cases.length} {t("similar cases from knowledge base")}
              </summary>
              <div style={{ marginTop: "8px" }}>
                {data.similar_cases.map((c, i) => (
                  <div key={i} style={{ fontSize: "11px", color: "var(--text-secondary)", padding: "6px 0", borderTop: "1px solid var(--border-subtle)" }}>
                    {c.user_query?.slice(0, 120)}…
                  </div>
                ))}
              </div>
            </details>
          )}

          <SourceList sources={data.sources} />
        </>
      )}
    </Panel>
  );
}

const contactLink = {
  fontSize: "13px", color: "var(--accent-secondary)", textDecoration: "none",
  display: "flex", alignItems: "center", gap: "8px",
};
const sectionLabel = {
  fontSize: "11px", fontWeight: 700, color: "var(--text-muted)",
  marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em",
};
