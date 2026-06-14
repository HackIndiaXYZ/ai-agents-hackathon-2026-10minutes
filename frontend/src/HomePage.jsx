// HomePage.jsx — Landing page (/) with a hero section that leads into /app

import React from "react";
import { useNavigate } from "react-router-dom";
import { useT } from "./i18n";
import "./index.css";

const features = [
  { titleKey: "Ask in any language", descKey: "Speak or type in your own language — we understand you." },
  { titleKey: "Find benefits", descKey: "Discover government schemes and help you're eligible for." },
  { titleKey: "Stay safe", descKey: "Spot frauds and scams before they reach you." },
];

export default function HomePage() {
  const navigate = useNavigate();
  const t = useT();

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      background: `radial-gradient(ellipse at 30% 15%, rgba(184,92,56,0.12) 0%, transparent 55%),
                   radial-gradient(ellipse at 75% 85%, rgba(154,74,44,0.10) 0%, transparent 55%),
                   var(--bg-primary)`,
      color: "var(--text-primary)",
      fontFamily: "var(--font-sans)",
    }}>
      {/* ── Top bar ── */}
      <header style={{
        display: "flex", alignItems: "center",
        padding: "20px 32px", flexShrink: 0,
      }}>
        <div
          onClick={() => navigate("/")}
          style={{ display: "flex", alignItems: "baseline", gap: "5px", cursor: "pointer" }}
        >
          <span style={{ fontSize: "18px", fontWeight: 700, color: "#3D2B1F", letterSpacing: "-0.01em" }}>
            Sahayak
          </span>
          <span style={{ fontSize: "18px", fontWeight: 500, color: "#B85C38" }}>
            AI
          </span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            onClick={() => navigate("/app")}
            style={{
              padding: "10px 20px",
              background: "transparent",
              border: "1px solid rgba(61,43,31,0.25)",
              borderRadius: "99px",
              color: "var(--text-primary)",
              fontSize: "14px", fontWeight: 600, cursor: "pointer",
              fontFamily: "var(--font-sans)",
              transition: "all 0.2s",
            }}
          >
            {t("Open App")}
          </button>
        </div>
      </header>

      {/* ── Hero ── */}
      <main style={{
        flex: 1, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        textAlign: "center", padding: "40px 24px",
      }}>
        <div className="animate-fade-in" style={{ maxWidth: "820px" }}>
          <div style={{
            fontSize: "13px", fontWeight: 700, letterSpacing: "0.12em",
            textTransform: "uppercase", color: "var(--accent-primary)",
            marginBottom: "24px",
          }}>
            {t("AI for financial inclusion")}
          </div>

          <h1 style={{
            fontSize: "clamp(34px, 6vw, 62px)",
            fontWeight: 800, lineHeight: 1.1, margin: "0 0 22px",
            letterSpacing: "-0.02em",
          }}>
            {t("Your personal guide to")}{" "}
            <span style={{
              background: "linear-gradient(135deg, #B85C38, #C97B54)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}>
              {t("money, benefits & safety")}
            </span>
          </h1>

          <p style={{
            fontSize: "clamp(15px, 2.2vw, 19px)",
            color: "var(--text-secondary)", lineHeight: 1.6,
            maxWidth: "580px", margin: "0 auto 40px",
          }}>
            {t("Sahayak AI helps you understand government schemes, manage your money, and stay safe from fraud — in your own language, free and simple.")}
          </p>

          <div style={{ display: "flex", gap: "14px", justifyContent: "center", flexWrap: "wrap" }}>
            <button
              className="cta-rise"
              onClick={() => navigate("/app")}
              style={{
                padding: "15px 36px",
                background: "linear-gradient(135deg, var(--accent-primary), #9a4a2c)",
                border: "none", borderRadius: "99px",
                color: "#fff", fontSize: "16px", fontWeight: 700,
                cursor: "pointer", fontFamily: "var(--font-sans)",
                boxShadow: "0 6px 20px rgba(184,92,56,0.3)",
              }}
            >
              {t("Get Started")}
            </button>
          </div>
        </div>

        {/* ── Feature highlights — no boxes ── */}
        <div className="animate-fade-in" style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "44px", marginTop: "80px",
          maxWidth: "960px", width: "100%",
        }}>
          {features.map((f) => (
            <div key={f.titleKey} style={{ textAlign: "left" }}>
              <div style={{
                width: "32px", height: "3px", borderRadius: "99px",
                background: "var(--accent-primary)", marginBottom: "16px",
              }} />
              <div style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px", color: "var(--text-primary)" }}>
                {t(f.titleKey)}
              </div>
              <div style={{ fontSize: "15px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {t(f.descKey)}
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* ── Footer ── */}
      <footer style={{
        padding: "24px 32px", textAlign: "center",
        fontSize: "13px", color: "var(--text-muted)",
        flexShrink: 0,
      }}>
        Sahayak AI · {t("Built for financial inclusion across India")}
      </footer>
    </div>
  );
}
