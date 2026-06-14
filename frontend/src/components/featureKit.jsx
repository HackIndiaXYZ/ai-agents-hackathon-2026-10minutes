// components/featureKit.jsx — Shared UI primitives for the feature panels.

import React from "react";
import { useT } from "../i18n";

export const Panel = ({ children, style, accent }) => (
  <div
    className="animate-scale-in"
    style={{
      background: "var(--bg-card)",
      border: `1px solid ${accent || "var(--border-subtle)"}`,
      borderRadius: "var(--radius-lg)",
      padding: "18px 20px",
      boxShadow: "var(--shadow-card)",
      ...style,
    }}
  >
    {children}
  </div>
);

export const SectionTitle = ({ icon, title, subtitle, right }) => (
  <div
    style={{
      display: "flex",
      alignItems: "flex-start",
      gap: "12px",
      marginBottom: "16px",
    }}
  >
    {icon && (
      <div
        style={{
          width: "38px",
          height: "38px",
          borderRadius: "11px",
          flexShrink: 0,
          background: "linear-gradient(135deg, var(--accent-primary), #7c3aed)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "18px",
          boxShadow: "var(--shadow-glow)",
        }}
      >
        {icon}
      </div>
    )}
    <div style={{ flex: 1 }}>
      <div
        style={{
          fontSize: "16px",
          fontWeight: 700,
          color: "var(--text-primary)",
        }}
      >
        {title}
      </div>
      {subtitle && (
        <div
          style={{
            fontSize: "12px",
            color: "var(--text-muted)",
            marginTop: "2px",
          }}
        >
          {subtitle}
        </div>
      )}
    </div>
    {right}
  </div>
);

export const LoadingState = ({ message = "Working…", rows = 3 }) => (
  <div className="animate-fade-in">
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        color: "var(--text-secondary)",
        fontSize: "13px",
        marginBottom: "14px",
      }}
    >
      {message}
    </div>
    {Array.from({ length: rows }).map((_, i) => (
      <div
        key={i}
        className="skeleton"
        style={{
          height: "54px",
          marginBottom: "10px",
          opacity: 1 - i * 0.18,
        }}
      />
    ))}
  </div>
);

export const ErrorState = ({ message, onRetry }) => {
  const t = useT();
  return (
    <div
      style={{
        padding: "16px 18px",
        background: "var(--red-dim)",
        border: "1px solid rgba(239,68,68,0.3)",
        borderRadius: "var(--radius-md)",
        color: "var(--red)",
        fontSize: "13px",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: "4px" }}>
        {t("Couldn't load this")}
      </div>
      <div style={{ color: "#fca5a5", lineHeight: 1.5 }}>{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            marginTop: "12px",
            padding: "7px 16px",
            background: "var(--red)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            color: "#fff",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {t("Retry")}
        </button>
      )}
    </div>
  );
};

export const EmptyState = ({ title, hint }) => (
  <div
    style={{
      flex: 1,
      minHeight: "320px",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      color: "var(--text-muted)",
      padding: "48px 24px",
    }}
  >
    <div
      style={{
        fontSize: "24px",
        fontWeight: 700,
        color: "var(--text-primary)",
        marginBottom: "12px",
      }}
    >
      {title}
    </div>
    {hint && (
      <div
        style={{
          fontSize: "16px",
          maxWidth: "440px",
          margin: "0 auto",
          lineHeight: 1.7,
        }}
      >
        {hint}
      </div>
    )}
  </div>
);

export const GroundedBadge = ({ grounded }) => {
  const t = useT();
  return (
    <span
      style={{
        fontSize: "10px",
        padding: "2px 9px",
        borderRadius: "99px",
        fontWeight: 700,
        background: grounded ? "var(--green-dim)" : "var(--amber-dim)",
        color: grounded ? "var(--green)" : "var(--amber)",
        border: `1px solid ${grounded ? "rgba(16,185,129,0.3)" : "rgba(245,158,11,0.3)"}`,
        whiteSpace: "nowrap",
      }}
    >
      {grounded ? `● ${t("LIVE WEB DATA")}` : `○ ${t("MODEL DATA")}`}
    </span>
  );
};

export const SourceList = ({ sources = [] }) => {
  const t = useT();
  if (!sources.length) return null;
  return (
    <div
      style={{
        marginTop: "16px",
        paddingTop: "14px",
        borderTop: "1px solid var(--border-subtle)",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          fontWeight: 700,
          color: "var(--text-muted)",
          marginBottom: "8px",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {t("Sources")} ({sources.length})
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
        {sources.map((s, i) => (
          <a
            key={i}
            href={s.uri}
            target="_blank"
            rel="noreferrer"
            style={{
              fontSize: "11px",
              color: "var(--accent-secondary)",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {s.title || s.uri}
          </a>
        ))}
      </div>
    </div>
  );
};

// Chip used across panels
export const Chip = ({
  children,
  color = "var(--accent-secondary)",
  filled = false,
}) => (
  <span
    style={{
      fontSize: "10px",
      padding: "2px 9px",
      borderRadius: "99px",
      fontWeight: 600,
      background: filled ? color : "var(--bg-input)",
      color: filled ? "#fff" : color,
      border: `1px solid ${filled ? color : "var(--border-subtle)"}`,
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </span>
);

// "No profile yet" guard shown when a feature needs a profile_id
export const NeedsProfile = ({ onGoToProfile }) => {
  const t = useT();
  return (
    <EmptyState
      title={t("Set up your profile first")}
      hint={
        <span>
          {t(
            "This feature personalises results to you. Create a profile and complete the quick assessment, then come back.",
          )}
          {onGoToProfile && (
            <>
              <br />
              <br />
              <button
                onClick={onGoToProfile}
                style={{
                  padding: "13px 28px",
                  background: "linear-gradient(135deg, var(--accent-primary), #9a4a2c)",
                  border: "none",
                  borderRadius: "99px",
                  color: "#fff",
                  fontSize: "15px",
                  fontWeight: 700,
                  cursor: "pointer",
                  boxShadow: "0 4px 16px rgba(184,92,56,0.3)",
                  fontFamily: "var(--font-sans)",
                }}
              >
                {t("Go to Profile & Assessment")}
              </button>
            </>
          )}
        </span>
      }
    />
  );
};
