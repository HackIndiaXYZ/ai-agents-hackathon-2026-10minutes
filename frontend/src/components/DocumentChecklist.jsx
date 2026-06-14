// components/DocumentChecklist.jsx — Document Checklist Generator panel

import React, { useState } from "react";
import { getDocumentChecklist } from "../api/client";
import { useT, useLang } from "../i18n";
import {
  Panel, SectionTitle, LoadingState, ErrorState, EmptyState,
  GroundedBadge, SourceList, Chip,
} from "./featureKit";

const SUGGESTIONS = [
  "Kisan Credit Card", "PM Kisan", "Ayushman Bharat card",
  "Ration card", "PM Mudra loan", "Old age pension", "New bank account (PMJDY)",
];

function DocRow({ doc, idx }) {
  const t = useT();
  const [checked, setChecked] = useState(false);
  return (
    <div style={{
      display: "flex", gap: "11px", padding: "11px 12px", marginBottom: "8px",
      background: "var(--bg-input)", borderRadius: "var(--radius-sm)",
      border: `1px solid ${checked ? "var(--green)" : "var(--border-subtle)"}`,
      transition: "border-color 0.2s",
    }}>
      <button
        onClick={() => setChecked((c) => !c)}
        style={{
          width: "22px", height: "22px", flexShrink: 0, marginTop: "1px",
          borderRadius: "6px", cursor: "pointer",
          border: `2px solid ${checked ? "var(--green)" : "var(--text-muted)"}`,
          background: checked ? "var(--green)" : "transparent",
          color: "#fff", fontSize: "12px", display: "flex",
          alignItems: "center", justifyContent: "center",
        }}
      >
        {checked ? "✓" : ""}
      </button>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "7px", flexWrap: "wrap", marginBottom: "3px" }}>
          <span style={{
            fontSize: "13px", fontWeight: 600,
            color: checked ? "var(--text-muted)" : "var(--text-primary)",
            textDecoration: checked ? "line-through" : "none",
          }}>
            {idx + 1}. {doc.name}
          </span>
          {doc.mandatory ? <Chip color="var(--red)">{t("Required")}</Chip> : <Chip>{t("Optional")}</Chip>}
          {doc.user_likely_has && <Chip color="var(--green)" filled>{t("You likely have this")}</Chip>}
        </div>
        {doc.why_needed && (
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5 }}>{doc.why_needed}</div>
        )}
        {!doc.user_likely_has && doc.where_to_get && (
          <div style={{ fontSize: "11px", color: "var(--amber)", marginTop: "4px" }}>
            ↪ {t("Get it:")} {doc.where_to_get}
          </div>
        )}
      </div>
    </div>
  );
}

export default function DocumentChecklist({ profile }) {
  const t = useT();
  const { lang } = useLang();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const run = async (service) => {
    const q = (service || input).trim();
    if (!q) return;
    setInput(q);
    setLoading(true); setError(""); setData(null);
    try {
      setData(await getDocumentChecklist({
        schemeOrService: q,
        profileId: profile?.profile_id || null,
        state: profile?.state || null,
        language: lang,  // follow the interface language, not the profile default
      }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const gathered = data ? data.documents.length : 0;

  return (
    <Panel>
      <SectionTitle
        icon="📋"
        title={t("Document Checklist")}
        subtitle={t("Know exactly what papers to bring — before you go")}
        right={data && <GroundedBadge grounded={data.grounded} />}
      />

      {/* Input */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "10px" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder={t("What do you want to apply for? e.g. Kisan Credit Card")}
          style={{
            flex: 1, padding: "10px 14px", background: "var(--bg-input)",
            border: "1px solid var(--border-active)", borderRadius: "var(--radius-sm)",
            color: "var(--text-primary)", fontSize: "13px", outline: "none",
          }}
        />
        <button onClick={() => run()} disabled={!input.trim() || loading} style={{
          padding: "10px 18px", background: input.trim() && !loading ? "var(--accent-primary)" : "var(--bg-card-hover)",
          border: "none", borderRadius: "var(--radius-sm)", color: "#fff",
          fontSize: "13px", fontWeight: 600, cursor: input.trim() && !loading ? "pointer" : "not-allowed",
          whiteSpace: "nowrap",
        }}>
          {loading ? "…" : t("Get list")}
        </button>
      </div>

      {/* Suggestions */}
      {!data && !loading && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "16px" }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => run(s)} style={{
              background: "var(--bg-input)", border: "1px solid var(--border-subtle)",
              borderRadius: "99px", padding: "5px 12px", fontSize: "11px",
              color: "var(--text-secondary)", cursor: "pointer",
            }}>{s}</button>
          ))}
        </div>
      )}

      {!data && !loading && !error && (
        <EmptyState icon="📄" title={t("Pick a scheme or service")} hint={t("We'll list the exact current documents for your state, what each is for, and where to get the ones you're missing.")} />
      )}
      {loading && <LoadingState message={t("Fetching the current document requirements…")} rows={4} />}
      {error && <ErrorState message={error} onRetry={() => run()} />}

      {data && (
        <>
          <div style={{ marginBottom: "12px" }}>
            <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>{data.scheme}</div>
            {data.summary && <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>{data.summary}</div>}
          </div>

          <div style={{ display: "flex", gap: "8px", marginBottom: "14px", flexWrap: "wrap" }}>
            {data.where_to_submit && <Chip color="var(--accent-secondary)">📍 {data.where_to_submit}</Chip>}
            {data.estimated_time && <Chip color="var(--amber)">⏱ {data.estimated_time}</Chip>}
            <Chip color="var(--green)">{gathered} {t("documents")}</Chip>
          </div>

          {data.documents.map((d, i) => <DocRow key={i} doc={d} idx={i} />)}

          {data.tips?.length > 0 && (
            <div style={{
              marginTop: "12px", padding: "10px 14px", background: "rgba(245,158,11,0.07)",
              border: "1px solid rgba(245,158,11,0.2)", borderRadius: "var(--radius-sm)",
            }}>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--amber)", marginBottom: "6px" }}>💡 TIPS</div>
              {data.tips.map((t, i) => (
                <div key={i} style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "3px", lineHeight: 1.5 }}>• {t}</div>
              ))}
            </div>
          )}

          <SourceList sources={data.sources} />
        </>
      )}
    </Panel>
  );
}
