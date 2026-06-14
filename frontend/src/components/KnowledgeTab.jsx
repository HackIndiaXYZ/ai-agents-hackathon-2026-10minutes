// components/KnowledgeTab.jsx — Dedicated "Knowledge" section: KG + Literacy Progress.

import React, { useState, useEffect } from "react";
import KnowledgeGraph from "./KnowledgeGraph";
import LiteracyProgress from "./LiteracyProgress";
import { getKnowledgeGraph } from "../api/client";
import { useT } from "../i18n";
import { EmptyState } from "./featureKit";

export default function KnowledgeTab({ profile, kg: kgProp, onGoToProfile }) {
  const t = useT();
  const [kg, setKg] = useState(kgProp || null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (kgProp) { setKg(kgProp); return; }
    if (profile?.profile_id) {
      setLoading(true);
      getKnowledgeGraph(profile.profile_id)
        .then((data) => data && setKg(data))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [profile, kgProp]);

  if (!profile?.profile_id) {
    return (
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "40px 0" }}>
        <EmptyState
          icon="🧠"
          title={t("No knowledge profile yet")}
          hint={
            <span>
              {t("Complete the assessment to build your knowledge graph and unlock the progress dashboard.")}
              <br /><br />
              {onGoToProfile && (
                <button onClick={onGoToProfile} style={{
                  padding: "8px 18px", background: "var(--accent-primary)", border: "none",
                  borderRadius: "var(--radius-sm)", color: "#fff", fontSize: "12px",
                  fontWeight: 600, cursor: "pointer",
                }}>{t("Go to Profile & Assessment →")}</button>
              )}
            </span>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "24px 0 48px" }}>
      <div style={{ marginBottom: "20px" }}>
        <div style={{ fontSize: "22px", fontWeight: 700, marginBottom: "4px" }}>{t("Your Knowledge")}</div>
        <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
          {t("A live map of what you know across the 5 financial domains, and how you're improving over time.")}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: "20px", alignItems: "start" }}>
        <div>
          {loading && !kg
            ? <div className="skeleton" style={{ height: "420px" }} />
            : <KnowledgeGraph kg={kg} profile={profile} />}
        </div>
        <div>
          <LiteracyProgress profile={profile} />
        </div>
      </div>
    </div>
  );
}
