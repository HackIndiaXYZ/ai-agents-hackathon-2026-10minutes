// components/ProfileSwitcher.jsx — Top-bar dropdown to switch the active user profile.

import React, { useState, useRef, useEffect } from "react";
import { useT } from "../i18n";

export default function ProfileSwitcher({ profiles = [], activeProfile, onSelect, onNew, theme = "dark" }) {
  const t = useT();
  const light = theme === "light";
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const label = activeProfile?.name || t("Select profile");

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={light ? {
          display: "flex", alignItems: "center", gap: "8px",
          padding: "6px 12px",
          background: "rgba(255,255,255,0.35)",
          border: `1px solid ${open ? "#B85C38" : "rgba(61,43,31,0.2)"}`,
          borderRadius: "99px", fontSize: "11px", cursor: "pointer",
          transition: "border-color 0.2s",
          fontFamily: '"Google Sans Flex", sans-serif',
        } : {
          display: "flex", alignItems: "center", gap: "8px",
          padding: "5px 12px",
          background: "var(--bg-card)",
          border: `1px solid ${open ? "var(--accent-primary)" : "var(--border-subtle)"}`,
          borderRadius: "99px", fontSize: "11px", cursor: "pointer",
          transition: "border-color 0.2s",
        }}
      >
        <div style={{
          width: "8px", height: "8px", borderRadius: "50%",
          background: activeProfile ? "var(--green)" : (light ? "rgba(61,43,31,0.4)" : "var(--text-muted)"),
          boxShadow: activeProfile ? "0 0 6px var(--green)" : "none",
        }} />
        <span style={{ color: light ? "#3D2B1F" : "var(--text-secondary)", fontWeight: light ? 500 : 400, maxWidth: "160px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {label}{activeProfile ? ` · ${activeProfile.literacy_level || t("not assessed")}` : ""}
        </span>
        <span style={{ color: light ? "rgba(61,43,31,0.5)" : "var(--text-muted)", fontSize: "9px" }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="animate-fade-in" style={{
          position: "absolute", right: 0, top: "calc(100% + 6px)", zIndex: 50,
          minWidth: "240px", maxHeight: "340px", overflowY: "auto",
          background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)", boxShadow: "var(--shadow-card)", padding: "6px",
        }}>
          <div style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", padding: "6px 8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {t("Switch profile")}
          </div>

          {profiles.length === 0 && (
            <div style={{ fontSize: "12px", color: "var(--text-muted)", padding: "8px" }}>
              {t("No profiles yet.")}
            </div>
          )}

          {profiles.map((p) => {
            const isActive = p.profile_id === activeProfile?.profile_id;
            return (
              <button
                key={p.profile_id}
                onClick={() => { onSelect(p); setOpen(false); }}
                style={{
                  width: "100%", display: "flex", alignItems: "center", gap: "10px",
                  padding: "8px 10px", marginBottom: "2px", textAlign: "left",
                  background: isActive ? "rgba(99,102,241,0.12)" : "transparent",
                  border: `1px solid ${isActive ? "var(--accent-primary)" : "transparent"}`,
                  borderRadius: "var(--radius-sm)", cursor: "pointer",
                }}
              >
                <div style={{
                  width: "28px", height: "28px", borderRadius: "50%", flexShrink: 0,
                  background: "linear-gradient(135deg, var(--accent-primary), #7c3aed)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "12px", fontWeight: 700, color: "#fff",
                }}>
                  {(p.name || "?").slice(0, 1).toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {p.name}
                  </div>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {p.occupation} · {p.state}
                  </div>
                </div>
                {isActive && <span style={{ color: "var(--green)", fontSize: "12px" }}>✓</span>}
              </button>
            );
          })}

          <div style={{ borderTop: "1px solid var(--border-subtle)", marginTop: "4px", paddingTop: "4px" }}>
            <button
              onClick={() => { onNew(); setOpen(false); }}
              style={{
                width: "100%", padding: "8px 10px", textAlign: "left",
                background: "transparent", border: "none", cursor: "pointer",
                color: "var(--accent-secondary)", fontSize: "12px", fontWeight: 600,
                borderRadius: "var(--radius-sm)",
              }}
            >
              ＋ {t("New profile")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
