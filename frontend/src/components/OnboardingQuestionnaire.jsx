// components/OnboardingQuestionnaire.jsx — Dynamic AI-generated financial literacy survey

import React, { useState, useEffect, useCallback } from "react";
import { getNextQuestion, completeOnboarding } from "../api/client";
import { useT } from "../i18n";

const DOMAIN_COLORS = {
  "Banking & Digital Payments": { bg: "rgba(59,130,246,0.12)", accent: "#3b82f6", icon: "🏦" },
  "Government Schemes":         { bg: "rgba(16,185,129,0.12)", accent: "#10b981", icon: "🏛️" },
  "Fraud & Cyber Safety":       { bg: "rgba(239,68,68,0.12)",  accent: "#ef4444", icon: "🛡️" },
  "Savings & Insurance":        { bg: "rgba(245,158,11,0.12)", accent: "#f59e0b", icon: "💰" },
  "Credit & Borrowing":         { bg: "rgba(168,85,247,0.12)", accent: "#a855f7", icon: "📋" },
};

const DOMAINS = Object.keys(DOMAIN_COLORS);

function DomainProgress({ answers }) {
  const coverage = {};
  DOMAINS.forEach((d) => (coverage[d] = 0));
  answers.forEach((a) => {
    if (a.question?.domain && coverage[a.question.domain] !== undefined) {
      coverage[a.question.domain]++;
    }
  });

  return (
    <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "20px" }}>
      {DOMAINS.map((d) => {
        const { accent, icon } = DOMAIN_COLORS[d];
        const count = coverage[d];
        return (
          <div key={d} style={{
            display: "flex", alignItems: "center", gap: "5px",
            padding: "4px 10px",
            background: count > 0 ? `rgba(${hexToRgb(accent)},0.15)` : "var(--bg-card)",
            border: `1px solid ${count > 0 ? accent : "var(--border-subtle)"}`,
            borderRadius: "99px",
            fontSize: "11px",
            color: count > 0 ? accent : "var(--text-muted)",
            fontWeight: count > 0 ? 600 : 400,
            transition: "all 0.3s",
          }}>
            <span>{icon}</span>
            <span>{d.split(" ")[0]}</span>
            {count > 0 && <span style={{
              background: accent, color: "#fff",
              borderRadius: "99px", padding: "0 5px", fontSize: "10px", fontWeight: 700,
            }}>{count}</span>}
          </div>
        );
      })}
    </div>
  );
}

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r},${g},${b}`;
}

function QuestionCard({ question, onAnswer, isLoading }) {
  const t = useT();
  const [selected, setSelected] = useState("");
  const [textAnswer, setTextAnswer] = useState("");

  useEffect(() => {
    setSelected("");
    setTextAnswer("");
  }, [question?.question_number]);

  if (!question) return null;

  const domainMeta = DOMAIN_COLORS[question.domain] || { bg: "rgba(99,102,241,0.1)", accent: "#6366f1", icon: "💡" };
  const isReady = question.question_type === "MCQ" ? !!selected : textAnswer.trim().length > 0;

  const handleSubmit = () => {
    if (!isReady) return;
    const answer = question.question_type === "MCQ" ? selected : textAnswer;
    onAnswer(answer);
  };

  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border-subtle)",
      borderRadius: "var(--radius-lg)",
      overflow: "hidden",
    }}>
      {/* Domain header */}
      <div style={{
        padding: "12px 20px",
        background: domainMeta.bg,
        borderBottom: "1px solid var(--border-subtle)",
        display: "flex", alignItems: "center", gap: "8px",
      }}>
        <span style={{ fontSize: "16px" }}>{domainMeta.icon}</span>
        <span style={{ fontSize: "12px", fontWeight: 600, color: domainMeta.accent }}>
          {question.domain}
        </span>
        <span style={{
          marginLeft: "auto", fontSize: "10px", padding: "2px 8px",
          borderRadius: "99px", background: "var(--bg-card)",
          border: "1px solid var(--border-subtle)",
          color: "var(--text-muted)",
        }}>
          {question.difficulty}
        </span>
      </div>

      {/* Question body */}
      <div style={{ padding: "24px 20px" }}>
        <div style={{
          fontSize: "15px", fontWeight: 500, lineHeight: 1.6,
          color: "var(--text-primary)", marginBottom: "20px",
        }}>
          {question.question_text}
        </div>

        {/* MCQ options */}
        {question.question_type === "MCQ" && question.options && (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {question.options.map((opt, i) => {
              const isSelected = selected === opt;
              return (
                <button
                  key={i}
                  onClick={() => setSelected(opt)}
                  style={{
                    padding: "12px 16px",
                    background: isSelected ? `rgba(${hexToRgb(domainMeta.accent)},0.15)` : "var(--bg-input)",
                    border: `1px solid ${isSelected ? domainMeta.accent : "var(--border-subtle)"}`,
                    borderRadius: "var(--radius-sm)",
                    color: isSelected ? domainMeta.accent : "var(--text-secondary)",
                    fontSize: "13px",
                    textAlign: "left",
                    cursor: "pointer",
                    transition: "all 0.15s",
                    fontWeight: isSelected ? 600 : 400,
                    fontFamily: "var(--font-sans)",
                  }}
                >
                  {opt}
                </button>
              );
            })}
          </div>
        )}

        {/* Short text */}
        {question.question_type === "SHORT_TEXT" && (
          <textarea
            value={textAnswer}
            onChange={(e) => setTextAnswer(e.target.value)}
            placeholder={t("Type your answer here…")}
            rows={3}
            style={{
              width: "100%",
              padding: "12px 14px",
              background: "var(--bg-input)",
              border: "1px solid var(--border-active)",
              borderRadius: "var(--radius-sm)",
              color: "var(--text-primary)",
              fontSize: "13px",
              fontFamily: "var(--font-sans)",
              resize: "vertical",
              outline: "none",
            }}
          />
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!isReady || isLoading}
          style={{
            marginTop: "16px",
            padding: "11px 24px",
            background: isReady && !isLoading ? domainMeta.accent : "var(--bg-card-hover)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            color: isReady && !isLoading ? "#fff" : "var(--text-muted)",
            fontSize: "13px",
            fontWeight: 600,
            cursor: isReady && !isLoading ? "pointer" : "not-allowed",
            transition: "all 0.2s",
          }}
        >
          {isLoading ? t("Loading next question…") : t("Next →")}
        </button>
      </div>
    </div>
  );
}

export default function OnboardingQuestionnaire({ profile, onComplete }) {
  const t = useT();
  const [answers, setAnswers] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState("");
  const [exiting, setExiting] = useState(false); // drives the fade-out before swap

  const fetchNextQuestion = useCallback(async (num, prevAnswers) => {
    setLoadingQuestion(true);
    setError("");
    try {
      const q = await getNextQuestion(profile.profile_id, prevAnswers, num);
      if (q.survey_complete) {
        await finalizeSurvey(prevAnswers);
      } else {
        setCurrentQuestion(q);
        setQuestionNumber(num);
      }
    } catch (err) {
      setError(t("Failed to load question. Please check the backend connection."));
    } finally {
      setLoadingQuestion(false);
    }
  }, [profile.profile_id]); // eslint-disable-line

  useEffect(() => {
    fetchNextQuestion(1, []);
  }, []); // eslint-disable-line

  const handleAnswer = async (answer) => {
    // Flatten key fields onto the entry so the backend coverage tracker reads
    // them whether it expects flat or nested shape.
    const entry = {
      question: currentQuestion,
      answer,
      domain: currentQuestion?.domain,
      concept: currentQuestion?.concept,
      question_text: currentQuestion?.question_text,
    };
    const newAnswers = [...answers, entry];

    // Play the exit animation, then hide the old card and load the next one
    setExiting(true);
    await new Promise((r) => setTimeout(r, 320));
    setAnswers(newAnswers);
    setCurrentQuestion(null);
    setExiting(false);
    await fetchNextQuestion(questionNumber + 1, newAnswers);
  };

  const finalizeSurvey = async (finalAnswers) => {
    setCompleting(true);
    try {
      const kg = await completeOnboarding(profile.profile_id, finalAnswers);
      onComplete(kg);
    } catch (err) {
      setError(t("Failed to save results. Please try again."));
      setCompleting(false);
    }
  };

  const progress = Math.min((questionNumber - 1) / 15 * 100, 100);

  return (
    <div style={{ maxWidth: "560px", margin: "0 auto", padding: "24px 0" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
          <div style={{ fontSize: "18px", fontWeight: 700 }}>
            {t("Financial Knowledge Assessment")}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            {Math.max(0, questionNumber - 1)}/12–15 {t("questions")}
          </div>
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px" }}>
          {t("Hi")} {profile.name}! {t("Answer these questions to help us understand your financial knowledge. There are no right or wrong answers — just be honest.")}
        </div>

        {/* Progress bar */}
        <div style={{
          height: "4px", borderRadius: "99px",
          background: "var(--border-subtle)", overflow: "hidden",
        }}>
          <div style={{
            height: "100%", width: `${progress}%`,
            background: "linear-gradient(90deg, var(--accent-primary), #818cf8)",
            borderRadius: "99px", transition: "width 0.4s ease",
          }} />
        </div>
      </div>

      {/* Domain coverage chips */}
      <DomainProgress answers={answers} />

      {/* Question card */}
      {completing ? (
        <div style={{
          padding: "40px 20px", textAlign: "center",
          background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
        }}>
          <div style={{ fontSize: "32px", marginBottom: "12px" }}>🧠</div>
          <div style={{ fontSize: "15px", fontWeight: 600, marginBottom: "6px" }}>
            {t("Building your knowledge graph…")}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            {t("Analysing your answers across all 5 financial domains")}
          </div>
          <div style={{ marginTop: "16px" }}>
            <div className="pulse-ring" style={{
              width: "12px", height: "12px", borderRadius: "50%",
              background: "var(--accent-primary)", margin: "0 auto",
            }} />
          </div>
        </div>
      ) : error ? (
        <div style={{
          padding: "20px", background: "var(--red-dim)",
          border: "1px solid var(--red)", borderRadius: "var(--radius-md)",
          color: "var(--red)", fontSize: "13px",
        }}>
          {error}
          <button
            onClick={() => fetchNextQuestion(questionNumber, answers)}
            style={{
              marginTop: "10px", display: "block",
              padding: "8px 16px", background: "var(--red)",
              border: "none", borderRadius: "var(--radius-sm)",
              color: "#fff", fontSize: "12px", cursor: "pointer",
            }}
          >
            {t("Retry")}
          </button>
        </div>
      ) : loadingQuestion && !currentQuestion ? (
        <div className="animate-fade-in" style={{
          padding: "48px 20px", textAlign: "center",
          background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
        }}>
          <div className="pulse-ring" style={{
            width: "12px", height: "12px", borderRadius: "50%",
            background: "var(--accent-primary)", margin: "0 auto 14px",
          }} />
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            {t("Preparing question")} {questionNumber}…
          </div>
        </div>
      ) : currentQuestion ? (
        <div
          key={questionNumber}
          className={exiting ? "question-exit" : "question-enter"}
        >
          <QuestionCard
            question={currentQuestion}
            onAnswer={handleAnswer}
            isLoading={loadingQuestion || exiting}
          />
        </div>
      ) : null}

      {/* Answer history (collapsed) */}
      {answers.length > 0 && (
        <details style={{ marginTop: "16px" }}>
          <summary style={{
            fontSize: "11px", color: "var(--text-muted)", cursor: "pointer",
            userSelect: "none", padding: "4px 0",
          }}>
            {answers.length} {t("answered")}
          </summary>
          <div style={{
            marginTop: "8px", display: "flex", flexDirection: "column", gap: "6px",
          }}>
            {answers.map((a, i) => {
              const domainMeta = DOMAIN_COLORS[a.question?.domain] || { accent: "#6366f1" };
              return (
                <div key={i} style={{
                  padding: "8px 12px",
                  background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)", fontSize: "11px",
                }}>
                  <span style={{ color: domainMeta.accent, fontWeight: 600 }}>
                    Q{i + 1}
                  </span>
                  <span style={{ color: "var(--text-secondary)", marginLeft: "8px" }}>
                    {a.question?.question_text?.slice(0, 60)}…
                  </span>
                  <span style={{ color: "var(--text-muted)", marginLeft: "8px" }}>
                    → {a.answer?.slice(0, 40)}
                  </span>
                </div>
              );
            })}
          </div>
        </details>
      )}
    </div>
  );
}
