// components/BenefitsHub.jsx — "Benefits & Help" hub hosting the action features.

import React, { useState } from "react";
import SchemeEligibility from "./SchemeEligibility";
import DocumentChecklist from "./DocumentChecklist";
import ComplaintGuide from "./ComplaintGuide";
import FraudAlertFeed from "./FraudAlertFeed";
import { useT } from "../i18n";

const SUBTABS = [
  { id: "schemes",    label: "My Schemes",    desc: "What you qualify for" },
  { id: "documents",  label: "Documents",     desc: "What papers to bring" },
  { id: "complaints", label: "File Complaint", desc: "Where & how to complain" },
  { id: "fraud",      label: "Fraud Alerts",  desc: "Live scam warnings" },
];

export default function BenefitsHub({ profile, onGoToProfile }) {
  const t = useT();
  const [sub, setSub] = useState("schemes");

  return (
    <div style={{
      minHeight: "100%", display: "flex", flexDirection: "column",
      maxWidth: "1080px", margin: "0 auto", width: "100%", padding: "40px 0 24px",
    }}>
      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{
          fontSize: "clamp(28px, 3.4vw, 40px)", fontWeight: 800,
          letterSpacing: "-0.02em", color: "var(--text-primary)", margin: 0,
        }}>
          {t("Benefits & Help")}
        </h1>
        <p style={{
          fontSize: "16px", color: "var(--text-secondary)",
          margin: "12px 0 0", maxWidth: "680px", lineHeight: 1.6,
        }}>
          {t("Real, current guidance — find your schemes, prep your documents, file complaints, and stay safe from fraud.")}
        </p>
      </div>

      {/* Sub-tab selector — pills, no boxes */}
      <div style={{
        display: "flex", gap: "10px", flexWrap: "wrap",
        paddingBottom: "26px", borderBottom: "1px solid rgba(61,43,31,0.14)",
      }}>
        {SUBTABS.map((tab) => {
          const active = sub === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setSub(tab.id)}
              title={t(tab.desc)}
              style={{
                display: "flex", flexDirection: "column", alignItems: "flex-start",
                gap: "2px", padding: "11px 22px", cursor: "pointer", textAlign: "left",
                background: active ? "rgba(184,92,56,0.14)" : "transparent",
                border: `1px solid ${active ? "rgba(184,92,56,0.4)" : "transparent"}`,
                borderRadius: "99px", transition: "all 0.2s",
                fontFamily: "var(--font-sans)",
              }}
            >
              <span style={{
                fontSize: "15px", fontWeight: active ? 700 : 600,
                color: active ? "var(--accent-primary)" : "var(--text-secondary)",
              }}>
                {t(tab.label)}
              </span>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                {t(tab.desc)}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active sub-feature — fills the rest of the viewport */}
      <div
        className="animate-fade-in"
        key={sub}
        style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", paddingTop: "28px" }}
      >
        {sub === "schemes" && <SchemeEligibility profile={profile} onGoToProfile={onGoToProfile} />}
        {sub === "documents" && <DocumentChecklist profile={profile} />}
        {sub === "complaints" && <ComplaintGuide profile={profile} />}
        {sub === "fraud" && <FraudAlertFeed profile={profile} />}
      </div>
    </div>
  );
}
