// components/DataLoopPanel.jsx — Adaptive data loop control panel.
//
// Shows how many real interactions are queued and how many anonymised rows are
// staged, and lets you (1) harvest queued interactions into the staging dataset,
// (2) preview the anonymised rows, and (3) promote them into the live RAG index.

import React, { useState, useEffect, useCallback } from "react";
import { getAdaptiveStats, harvestAdaptive, previewAdaptive, ingestAdaptive } from "../api/client";
import { useT } from "../i18n";
import { ErrorState, Chip } from "./featureKit";

const BORDER = "rgba(61,43,31,0.16)";

function Stat({ value, label, color }) {
  return (
    <div style={{ minWidth: "140px" }}>
      <div style={{ fontSize: "42px", fontWeight: 800, color: color || "var(--accent-primary)", lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
    </div>
  );
}

const btn = (bg, disabled) => ({
  padding: "13px 26px", background: disabled ? "var(--agent-pending)" : bg,
  border: "none", borderRadius: "99px", color: "#fff",
  fontSize: "15px", fontWeight: 700, cursor: disabled ? "not-allowed" : "pointer",
  fontFamily: "var(--font-sans)",
});

const sectionHead = {
  fontSize: "22px", fontWeight: 700, color: "var(--text-primary)", margin: 0,
};

export default function DataLoopPanel() {
  const t = useT();
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState("");        // "harvest" | "ingest" | "preview"
  const [msg, setMsg] = useState(null);        // { kind: "ok"|"err", text }
  const [error, setError] = useState("");

  const loadStats = useCallback(async () => {
    setError("");
    try { setStats(await getAdaptiveStats()); }
    catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const onHarvest = async () => {
    setBusy("harvest"); setMsg(null);
    try {
      const r = await harvestAdaptive();
      setMsg({ kind: "ok", text: t("Harvested") + ` ${r.processed} → ` + t("wrote") + ` ${r.written} ` + t("new rows") + ` (${r.skipped_duplicates} ` + t("duplicates skipped") + `)` });
      await loadStats();
    } catch (e) { setMsg({ kind: "err", text: e.message }); }
    finally { setBusy(""); }
  };

  const onPreview = async () => {
    setBusy("preview"); setMsg(null);
    try { const r = await previewAdaptive(10); setRows(r.rows || []); }
    catch (e) { setMsg({ kind: "err", text: e.message }); }
    finally { setBusy(""); }
  };

  const onIngest = async () => {
    if (!window.confirm(t("Promote all staged rows into the live RAG index? This embeds them into Qdrant and can take a few minutes."))) return;
    setBusy("ingest"); setMsg(null);
    try {
      const r = await ingestAdaptive();
      setMsg({ kind: "ok", text: t("Promoted staged rows into collection") + ` "${r.collection}".` });
      await loadStats();
    } catch (e) { setMsg({ kind: "err", text: e.message }); }
    finally { setBusy(""); }
  };

  return (
    <div style={{ maxWidth: "920px", margin: "0 auto", padding: "40px 0 48px" }}>
      {/* Header */}
      <h1 style={{
        fontSize: "clamp(28px, 3.4vw, 40px)", fontWeight: 800,
        letterSpacing: "-0.02em", color: "var(--text-primary)", margin: 0,
      }}>
        {t("Adaptive Data Loop")}
      </h1>
      <p style={{ fontSize: "16px", color: "var(--text-secondary)", lineHeight: 1.6, margin: "12px 0 0", maxWidth: "740px" }}>
        {t("Real user interactions (chat answers, checklists, complaints, scheme lookups) are captured, then anonymised and reformatted into the dataset schema. You review the staged rows and promote them into the live RAG index — nothing is published automatically.")}
      </p>

      {/* Pipeline status — no box */}
      <div style={{ marginTop: "40px", paddingTop: "28px", borderTop: `1px solid ${BORDER}` }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", marginBottom: "24px" }}>
          <div style={{ flex: 1 }}>
            <h2 style={sectionHead}>{t("Pipeline status")}</h2>
            <div style={{ fontSize: "14px", color: "var(--text-muted)", marginTop: "4px" }}>
              {t("Queued interactions → anonymised staging → live RAG")}
            </div>
          </div>
          <button onClick={loadStats} style={{
            padding: "9px 18px", background: "transparent", border: `1px solid ${BORDER}`,
            borderRadius: "99px", color: "var(--text-secondary)", fontSize: "13px",
            cursor: "pointer", fontFamily: "var(--font-sans)", fontWeight: 600,
          }}>{t("Refresh")}</button>
        </div>

        {error && <ErrorState message={error} onRetry={loadStats} />}

        {stats && (
          <>
            <div style={{ display: "flex", gap: "56px", marginBottom: "14px", flexWrap: "wrap" }}>
              <Stat value={stats.queued_events} label={t("Queued interactions")} color="var(--amber)" />
              <Stat value={stats.staged_rows} label={t("Staged dataset rows")} color="var(--green)" />
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", marginBottom: "24px", wordBreak: "break-all" }}>
              {stats.staging_path}
            </div>

            {/* Step buttons */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
              <button onClick={onHarvest} disabled={!!busy || stats.queued_events === 0} style={btn("var(--accent-primary)", !!busy || stats.queued_events === 0)}>
                {busy === "harvest" ? t("Harvesting…") : `${t("Harvest queued")} (${stats.queued_events})`}
              </button>
              <button onClick={onPreview} disabled={!!busy || stats.staged_rows === 0} style={btn("#6b7d8a", !!busy || stats.staged_rows === 0)}>
                {busy === "preview" ? t("Loading…") : t("Preview staged")}
              </button>
              <button onClick={onIngest} disabled={!!busy || stats.staged_rows === 0} style={btn("var(--green)", !!busy || stats.staged_rows === 0)}>
                {busy === "ingest" ? t("Promoting…") : t("Promote to RAG")}
              </button>
            </div>

            {msg && (
              <div style={{
                marginTop: "16px", padding: "12px 16px", borderRadius: "14px", fontSize: "14px",
                background: msg.kind === "ok" ? "var(--green-dim)" : "var(--red-dim)",
                color: msg.kind === "ok" ? "var(--green)" : "var(--red)",
                border: `1px solid ${msg.kind === "ok" ? "rgba(16,133,89,0.3)" : "rgba(220,38,38,0.3)"}`,
              }}>
                {msg.text}
              </div>
            )}
          </>
        )}
      </div>

      {/* Preview of anonymised staged rows — no box */}
      {rows && (
        <div style={{ marginTop: "40px", paddingTop: "28px", borderTop: `1px solid ${BORDER}` }}>
          <h2 style={sectionHead}>{t("Anonymised staged rows")}</h2>
          <div style={{ fontSize: "14px", color: "var(--text-muted)", margin: "4px 0 20px" }}>
            {t("These are what would be added to the dataset — verify no personal data remains")}
          </div>
          {rows.length === 0 && <div style={{ fontSize: "14px", color: "var(--text-muted)" }}>{t("No staged rows yet. Harvest first.")}</div>}
          {rows.map((r, i) => (
            <div key={i} style={{
              padding: "16px 18px", marginBottom: "12px",
              background: "rgba(255,255,255,0.5)", border: `1px solid ${BORDER}`,
              borderRadius: "16px",
            }}>
              <div style={{ display: "flex", gap: "7px", flexWrap: "wrap", marginBottom: "8px" }}>
                <Chip color="var(--accent-primary)">{r.domain_category}</Chip>
                {r.subdomain && <Chip>{r.subdomain}</Chip>}
                <Chip color="var(--green)">{r.source}</Chip>
              </div>
              <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "6px" }}>
                {r.user_query}
              </div>
              <div style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, maxHeight: "80px", overflow: "hidden" }}>
                {(r.enhanced_completion || "").slice(0, 280)}…
              </div>
              {r.userprofile && (
                <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "8px", fontStyle: "italic" }}>
                  {r.userprofile}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
