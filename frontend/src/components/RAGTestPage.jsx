// components/RAGTestPage.jsx — Retrieval test page
import React, { useState } from "react";
import { searchRAG } from "../api/client";

const BORDER = "rgba(61,43,31,0.16)";

// ── Score bar ─────────────────────────────────────────────────────────────────
const ScoreBar = ({ score, label }) => {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.75
      ? "var(--green)"
      : score >= 0.55
        ? "var(--amber)"
        : score >= 0.35
          ? "var(--blue)"
          : "var(--text-muted)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <span
        style={{
          fontSize: "12px",
          color: "var(--text-muted)",
          minWidth: "66px",
        }}
      >
        {label}
      </span>
      <div
        style={{
          flex: 1,
          height: "5px",
          background: "rgba(61,43,31,0.1)",
          borderRadius: "99px",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: "99px",
            transition: "width 0.6s ease",
          }}
        />
      </div>
      <span
        style={{
          fontSize: "12px",
          color,
          fontWeight: 700,
          fontFamily: "var(--font-mono)",
          minWidth: "36px",
        }}
      >
        {pct}%
      </span>
    </div>
  );
};

// ── Single question card ──────────────────────────────────────────────────────
const QuestionCard = ({ q }) => {
  const [expanded, setExpanded] = useState(false);
  const actions = q.actions || [];
  const shown = expanded ? actions : actions.slice(0, 3);
  const isTop = q.rank === 1;

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.5)",
        border: `1px solid ${isTop ? "rgba(184,92,56,0.45)" : BORDER}`,
        borderRadius: "20px",
        padding: "20px",
        position: "relative",
        transition: "border-color 0.2s",
      }}
    >
      {/* Rank badge */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          right: "16px",
          width: "30px",
          height: "30px",
          borderRadius: "50%",
          background: isTop ? "var(--accent-primary)" : "rgba(255,255,255,0.6)",
          border: `1px solid ${isTop ? "var(--accent-primary)" : BORDER}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "12px",
          fontWeight: 700,
          color: isTop ? "#fff" : "var(--text-muted)",
        }}
      >
        #{q.rank}
      </div>

      {/* Question */}
      <div
        style={{
          fontSize: "16px",
          fontWeight: 600,
          lineHeight: "1.5",
          color: "var(--text-primary)",
          paddingRight: "40px",
          marginBottom: "14px",
        }}
      >
        {q.user_query}
      </div>

      {/* Metadata chips */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "6px",
          marginBottom: "14px",
        }}
      >
        {q.domain_category && (
          <span
            style={{
              fontSize: "12px",
              padding: "3px 10px",
              borderRadius: "99px",
              background: "var(--blue-dim)",
              color: "var(--blue)",
              fontWeight: 600,
            }}
          >
            {q.domain_category}
          </span>
        )}
        {q.subdomain && (
          <span
            style={{
              fontSize: "12px",
              padding: "3px 10px",
              borderRadius: "99px",
              background: "rgba(184,92,56,0.12)",
              color: "var(--accent-primary)",
              fontWeight: 600,
            }}
          >
            {q.subdomain}
          </span>
        )}
        <span
          style={{
            fontSize: "12px",
            padding: "3px 10px",
            borderRadius: "99px",
            background: "rgba(255,255,255,0.6)",
            color: "var(--text-secondary)",
            border: `1px solid ${BORDER}`,
          }}
        >
          {q.language_name}
        </span>
      </div>

      {/* Scores */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "7px",
          marginBottom: "14px",
        }}
      >
        <ScoreBar score={q.rerank_score} label="Rerank" />
        <ScoreBar score={q.retrieval_score} label="Hybrid" />
      </div>

      {/* Actions */}
      {actions.length > 0 && (
        <div>
          <div
            style={{
              fontSize: "11px",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
              marginBottom: "8px",
            }}
          >
            Suggested Actions
          </div>
          <ol style={{ paddingLeft: "18px", margin: 0 }}>
            {shown.map((a, i) => (
              <li
                key={i}
                style={{
                  fontSize: "14px",
                  color: "var(--text-secondary)",
                  lineHeight: "1.6",
                  marginBottom: "5px",
                }}
              >
                {a}
              </li>
            ))}
          </ol>
          {actions.length > 3 && (
            <button
              onClick={() => setExpanded((x) => !x)}
              style={{
                marginTop: "8px",
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--accent-primary)",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "0",
              }}
            >
              {expanded ? "Show less" : `+${actions.length - 3} more`}
            </button>
          )}
        </div>
      )}

      {/* Source */}
      {q.source && (
        <div
          style={{
            marginTop: "14px",
            paddingTop: "14px",
            borderTop: `1px solid ${BORDER}`,
            fontSize: "13px",
            color: "var(--text-muted)",
          }}
        >
          {q.source.split(",")[0].trim()}
        </div>
      )}
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────
export default function RAGTestPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    const q = query.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await searchRAG(q);
      setResults(data);
    } catch (err) {
      setError(
        err.message ||
          "Search failed. Is the backend running and collection indexed?",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSearch();
  };

  const canSearch = query.trim().length > 0 && !loading;

  return (
    <div
      style={{
        height: "100%",
        overflowY: "auto",
        padding: "40px 32px",
        maxWidth: "1280px",
        margin: "0 auto",
      }}
    >
      {/* ── Header: title only ── */}
      <h1
        style={{
          fontSize: "clamp(30px, 4vw, 44px)",
          fontWeight: 800,
          letterSpacing: "-0.02em",
          color: "var(--text-primary)",
          margin: "0 0 28px",
        }}
      >
        RAG Pipeline Test
      </h1>

      {/* ── Search box ── */}
      <div style={{ marginBottom: "32px" }}>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about financial fraud in any language…"
          style={{
            width: "100%",
            minHeight: "240px",
            background: "rgba(255,255,255,0.55)",
            border: `1px solid ${BORDER}`,
            borderRadius: "22px",
            padding: "24px 26px",
            color: "var(--text-primary)",
            fontSize: "19px",
            fontFamily: "var(--font-sans)",
            lineHeight: "1.6",
            resize: "vertical",
            outline: "none",
            marginBottom: "16px",
            boxSizing: "border-box",
            transition: "border-color 0.2s",
          }}
          onFocus={(e) =>
            (e.target.style.borderColor = "var(--accent-primary)")
          }
          onBlur={(e) => (e.target.style.borderColor = BORDER)}
        />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>
            Ctrl+Enter to search · works in any Indian language
          </span>
          <button
            onClick={handleSearch}
            disabled={!canSearch}
            style={{
              padding: "14px 30px",
              background: canSearch
                ? "linear-gradient(135deg, var(--accent-primary), #9a4a2c)"
                : "var(--agent-pending)",
              border: "none",
              borderRadius: "99px",
              color: "#fff",
              fontSize: "15px",
              fontWeight: 700,
              cursor: canSearch ? "pointer" : "not-allowed",
              transition: "all 0.2s",
              fontFamily: "var(--font-sans)",
              boxShadow: canSearch ? "0 4px 16px rgba(184,92,56,0.3)" : "none",
            }}
          >
            {loading ? "Searching…" : "Search Similar Questions"}
          </button>
        </div>
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <div style={{ fontSize: "17px", color: "var(--text-secondary)" }}>
            Running pipeline…
          </div>
          <div
            style={{
              marginTop: "10px",
              fontSize: "14px",
              color: "var(--text-muted)",
            }}
          >
            The first run loads the models and can take a couple of minutes.
            Later queries are fast.
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div
          style={{
            padding: "16px 20px",
            background: "var(--red-dim)",
            border: "1px solid rgba(220,38,38,0.3)",
            borderRadius: "16px",
            color: "var(--red)",
            fontSize: "15px",
            marginBottom: "24px",
          }}
        >
          {error}
        </div>
      )}

      {/* ── Results ── */}
      {results && !loading && (
        <>
          {/* Synthesized answer */}
          <div
            style={{
              marginBottom: "32px",
              background: "rgba(255,255,255,0.55)",
              border: `1px solid ${BORDER}`,
              borderRadius: "22px",
              overflow: "hidden",
            }}
          >
            {/* Panel header */}
            <div
              style={{
                padding: "16px 22px",
                background: "rgba(184,92,56,0.1)",
                borderBottom: `1px solid ${BORDER}`,
                display: "flex",
                alignItems: "center",
                gap: "10px",
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  fontSize: "16px",
                  fontWeight: 700,
                  color: "var(--accent-primary)",
                }}
              >
                Synthesized Answer
              </span>
              <div
                style={{
                  marginLeft: "auto",
                  display: "flex",
                  gap: "8px",
                  alignItems: "center",
                }}
              >
                <span
                  style={{
                    fontSize: "12px",
                    padding: "3px 10px",
                    borderRadius: "99px",
                    background: "rgba(184,92,56,0.14)",
                    color: "var(--accent-primary)",
                  }}
                >
                  {results.query_language}
                </span>
                <span
                  style={{
                    fontSize: "12px",
                    padding: "3px 10px",
                    borderRadius: "99px",
                    background: "var(--green-dim)",
                    color: "var(--green)",
                  }}
                >
                  top {results.similar_questions.length} results
                </span>
              </div>
            </div>

            {/* Answer text */}
            <div
              style={{
                padding: "24px 26px",
                fontSize: "17px",
                lineHeight: "1.8",
                color: "var(--text-primary)",
                whiteSpace: "pre-wrap",
              }}
            >
              {results.gemini_answer}
            </div>
          </div>

          {/* Similar questions section */}
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                marginBottom: "20px",
              }}
            >
              <h2
                style={{
                  fontSize: "22px",
                  fontWeight: 700,
                  color: "var(--text-primary)",
                  margin: 0,
                }}
              >
                Similarly Asked Questions
              </h2>
              <span
                style={{
                  fontSize: "12px",
                  padding: "3px 10px",
                  borderRadius: "99px",
                  background: "var(--blue-dim)",
                  color: "var(--blue)",
                  fontWeight: 700,
                }}
              >
                {results.similar_questions.length} from dataset
              </span>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
                gap: "18px",
              }}
            >
              {results.similar_questions.map((q) => (
                <QuestionCard key={q.rank} q={q} />
              ))}
            </div>
          </div>
        </>
      )}

      {/* ── Empty state ── */}
    </div>
  );
}
