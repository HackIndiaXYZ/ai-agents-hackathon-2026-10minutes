// components/FraudAlertFeed.jsx — Live Fraud Alert Feed (Google News RSS)

import React, { useState, useEffect, useCallback } from "react";
import { getFraudAlerts } from "../api/client";
import { useT, useLang } from "../i18n";
import {
  Panel, SectionTitle, LoadingState, ErrorState, EmptyState, Chip,
} from "./featureKit";

function AlertCard({ alert }) {
  const t = useT();
  return (
    <div style={{
      padding: "13px 15px", marginBottom: "10px",
      background: "var(--bg-input)", borderRadius: "var(--radius-md)",
      border: "1px solid var(--border-subtle)", borderLeft: "3px solid var(--red)",
    }}>
      <div style={{ display: "flex", gap: "7px", flexWrap: "wrap", marginBottom: "7px", alignItems: "center" }}>
        {alert.scam_type && <Chip color="var(--red)" filled>⚠ {alert.scam_type}</Chip>}
        {alert.publisher && <Chip>{alert.publisher}</Chip>}
        {alert.published_relative && (
          <span style={{ fontSize: "10px", color: "var(--text-muted)", marginLeft: "auto" }}>{alert.published_relative}</span>
        )}
      </div>

      <a href={alert.link} target="_blank" rel="noreferrer" style={{
        fontSize: "13px", fontWeight: 600, color: "var(--text-primary)",
        textDecoration: "none", lineHeight: 1.4, display: "block",
      }}>
        {alert.title}
      </a>

      {alert.who_is_targeted && (
        <div style={{ fontSize: "11px", color: "var(--amber)", marginTop: "6px" }}>
          🎯 {t("Targets:")} {alert.who_is_targeted}
        </div>
      )}
      {alert.prevention_tip && (
        <div style={{
          fontSize: "12px", color: "var(--text-secondary)", marginTop: "7px",
          padding: "7px 10px", background: "rgba(16,185,129,0.07)",
          borderRadius: "var(--radius-sm)", lineHeight: 1.5,
        }}>
          🛡 {alert.prevention_tip}
        </div>
      )}
    </div>
  );
}

export default function FraudAlertFeed({ profile }) {
  const t = useT();
  const { lang } = useLang();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      setData(await getFraudAlerts({
        state: profile?.state || null,
        profileId: profile?.profile_id || null,
        limit: 10,
        language: lang,
      }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [profile, lang]);

  useEffect(() => { load(); }, [load]);

  return (
    <Panel accent="rgba(239,68,68,0.25)">
      <SectionTitle
        icon="🚨"
        title={t("Live Fraud Alerts")}
        subtitle={data ? `${t("Recent scams near")} ${data.state} · ${t("live news")}` : t("Recent financial scams in your area")}
        right={
          <button onClick={load} disabled={loading} style={{
            padding: "6px 12px", background: "var(--bg-card-hover)", border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)", color: "var(--text-secondary)", fontSize: "11px",
            cursor: loading ? "default" : "pointer", whiteSpace: "nowrap",
          }}>↻ {t("Refresh")}</button>
        }
      />

      {/* Helplines bar */}
      {data?.helplines && (
        <div style={{
          display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px",
          padding: "10px 12px", background: "rgba(239,68,68,0.06)",
          border: "1px solid rgba(239,68,68,0.2)", borderRadius: "var(--radius-sm)",
        }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--red)", marginRight: "2px" }}>
            {t("VICTIM OF FRAUD? ACT NOW:")}
          </span>
          {data.helplines.map((h, i) => (
            <a key={i}
               href={h.value.startsWith("http") ? h.value : `tel:${h.value}`}
               target={h.value.startsWith("http") ? "_blank" : undefined}
               rel="noreferrer"
               style={{ fontSize: "11px", color: "var(--accent-secondary)", textDecoration: "none", fontWeight: 600 }}>
              {h.label}: {h.value}
            </a>
          ))}
        </div>
      )}

      {loading && !data && <LoadingState message={t("Fetching live fraud news for your area…")} rows={4} />}
      {error && <ErrorState message={error} onRetry={load} />}

      {data && data.alerts.length === 0 && !loading && (
        <EmptyState icon="✅" title={t("No recent alerts found")} hint={t("No fresh fraud news surfaced for your area right now. Stay alert and check back later.")} />
      )}

      {data && data.alerts.map((a, i) => <AlertCard key={i} alert={a} />)}

      {data && (
        <div style={{ fontSize: "10px", color: "var(--text-muted)", textAlign: "right", marginTop: "8px" }}>
          Source: {data.source}
        </div>
      )}
    </Panel>
  );
}
