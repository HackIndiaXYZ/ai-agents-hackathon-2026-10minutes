// components/ProfileSetup.jsx — User profile creation form

import React, { useState } from "react";
import { createProfile } from "../api/client";
import { useT } from "../i18n";

const STATES = [
  "Andhra Pradesh","Assam","Bihar","Chhattisgarh","Delhi","Goa","Gujarat",
  "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
  "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
  "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh",
  "Uttarakhand","West Bengal","Other",
];

const OCCUPATIONS = [
  "Farmer / Agricultural Worker",
  "Daily Wage Laborer",
  "Small Business Owner / Shopkeeper",
  "Self-Employed / Artisan",
  "Government Employee",
  "Private Sector Employee",
  "Student",
  "Homemaker",
  "Retired",
  "Other",
];

const LANGUAGES = [
  "English","Hindi","Bengali","Telugu","Marathi","Tamil","Urdu","Gujarati",
  "Kannada","Malayalam","Odia","Punjabi","Assamese","Other",
];

const AGE_GROUPS = ["Under 18","18-25","26-35","36-50","50+"];
const EDUCATION = ["No formal education","Primary","Secondary","Higher Secondary","Graduate","Post Graduate"];

const BORDER = "rgba(61,43,31,0.16)";

const inputStyle = {
  width: "100%",
  padding: "14px 16px",
  background: "rgba(255,255,255,0.6)",
  border: `1px solid ${BORDER}`,
  borderRadius: "14px",
  color: "var(--text-primary)",
  fontSize: "15px",
  fontFamily: "var(--font-sans)",
  outline: "none",
  transition: "border-color 0.2s",
};

const labelStyle = {
  display: "block",
  fontSize: "12px",
  fontWeight: 600,
  color: "var(--text-secondary)",
  marginBottom: "8px",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
};

const fieldStyle = { marginBottom: "18px" };

// Left-column copy that changes with each form step
const STEP_COPY = [
  {
    heading: "Welcome to Sahayak AI",
    sub: "Your friendly guide to government schemes, savings, and staying safe from fraud — in your language. Let's start with a few quick details.",
  },
  {
    heading: "Where you live and work",
    sub: "This helps us match you with the schemes, subsidies, and guidance that actually apply to your state and your kind of work.",
  },
  {
    heading: "Set your preferences",
    sub: "A few last details so we can speak your language and tailor every answer to your situation.",
  },
];

export default function ProfileSetup({ onProfileCreated, existingProfiles = [] }) {
  const t = useT();
  const [form, setForm] = useState({
    name: "",
    age_group: "26-35",
    state: "",
    occupation: "",
    preferred_language: "Hindi",
    gender: "",
    education_level: "",
    has_smartphone: true,
    has_bank_account: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedExisting, setSelectedExisting] = useState("");
  const [step, setStep] = useState(0);

  const STEPS = [
    { title: t("The basics") },
    { title: t("You & your work") },
    { title: t("Preferences") },
  ];

  const set = (key) => (e) => {
    const val = e.target.type === "checkbox" ? e.target.checked
              : e.target.value === "true" ? true
              : e.target.value === "false" ? false
              : e.target.value;
    setForm((p) => ({ ...p, [key]: val }));
  };

  const validateStep = (s) => {
    if (s === 0 && !form.name.trim()) return t("Name is required.");
    if (s === 1 && !form.state) return t("Please select your state.");
    if (s === 1 && !form.occupation) return t("Please select your occupation.");
    return "";
  };

  const goNext = async () => {
    const err = validateStep(step);
    if (err) return setError(err);
    setError("");
    if (step < STEPS.length - 1) { setStep((s) => s + 1); return; }
    // Final step → create the profile
    setLoading(true);
    try {
      const profile = await createProfile(form);
      onProfileCreated(profile);
    } catch (err2) {
      setError(t("Failed to save profile. Is the backend running?"));
    } finally {
      setLoading(false);
    }
  };

  const goBack = () => { setError(""); setStep((s) => Math.max(0, s - 1)); };

  const handleSelectExisting = () => {
    const p = existingProfiles.find((x) => x.profile_id === selectedExisting);
    if (p) onProfileCreated(p);
  };

  const copy = STEP_COPY[step] || STEP_COPY[0];

  return (
    <div style={{
      display: "flex", gap: "56px", alignItems: "center", flexWrap: "wrap",
      maxWidth: "1120px", margin: "0 auto", padding: "40px 0", minHeight: "100%",
    }}>
      {/* ── Left: step-aware copy (no box) ── */}
      <div style={{
        flex: "1 1 320px", minWidth: "280px",
        display: "flex", flexDirection: "column", justifyContent: "center",
      }}>
        <div key={`eyebrow-${step}`} className="animate-fade-in" style={{
          fontSize: "13px", fontWeight: 700, letterSpacing: "0.08em",
          textTransform: "uppercase", color: "var(--accent-primary)", marginBottom: "16px",
        }}>
          {t("Step")} {step + 1} {t("of")} {STEPS.length} · {STEPS[step].title}
        </div>
        <h1 key={`head-${step}`} className="animate-fade-in" style={{
          fontSize: "clamp(32px, 4.2vw, 46px)", fontWeight: 800,
          lineHeight: 1.12, letterSpacing: "-0.02em",
          color: "var(--text-primary)", margin: "0 0 18px",
        }}>
          {t(copy.heading)}
        </h1>
        <p key={`sub-${step}`} className="animate-fade-in" style={{
          fontSize: "17px", lineHeight: 1.7, color: "var(--text-secondary)",
          maxWidth: "440px", margin: 0,
        }}>
          {t(copy.sub)}
        </p>
      </div>

      {/* ── Right: form + trust badges ── */}
      <div style={{ flex: "1 1 460px", minWidth: "300px", maxWidth: "560px", width: "100%" }}>
        {/* Existing profiles */}
        {existingProfiles.length > 0 && (
          <div style={{
            padding: "16px 18px",
            background: "rgba(255,255,255,0.5)",
            border: `1px solid ${BORDER}`,
            borderRadius: "18px",
            marginBottom: "16px",
          }}>
            <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "10px", color: "var(--text-secondary)", letterSpacing: "0.04em" }}>
              {t("CONTINUE AS EXISTING USER")}
            </div>
            <div style={{ display: "flex", gap: "10px" }}>
              <select
                value={selectedExisting}
                onChange={(e) => setSelectedExisting(e.target.value)}
                style={{ ...inputStyle, flex: 1 }}
              >
                <option value="">{t("Select profile…")}</option>
                {existingProfiles.map((p) => (
                  <option key={p.profile_id} value={p.profile_id}>
                    {p.name} — {p.occupation} ({p.state})
                  </option>
                ))}
              </select>
              <button
                onClick={handleSelectExisting}
                disabled={!selectedExisting}
                style={{
                  padding: "12px 22px",
                  background: selectedExisting ? "var(--accent-primary)" : "var(--agent-pending)",
                  border: "none",
                  borderRadius: "99px",
                  color: "#fff",
                  fontSize: "14px",
                  cursor: selectedExisting ? "pointer" : "not-allowed",
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                }}
              >
                {t("Continue")}
              </button>
            </div>
          </div>
        )}

        {/* Stepped profile card */}
        <div style={{
          padding: "28px",
          background: "rgba(255,255,255,0.55)",
          border: `1px solid ${BORDER}`,
          borderRadius: "24px",
          boxShadow: "var(--shadow-card)",
        }}>
          {/* Step progress */}
          <div style={{ display: "flex", alignItems: "center", gap: "0", marginBottom: "26px" }}>
            {STEPS.map((s, i) => {
              const done = i < step, active = i === step;
              return (
                <React.Fragment key={i}>
                  <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                    <div style={{
                      width: "34px", height: "34px", borderRadius: "50%",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "14px", fontWeight: 700,
                      background: active ? "var(--accent-primary)" : done ? "var(--green-dim)" : "rgba(255,255,255,0.6)",
                      border: `1px solid ${active ? "var(--accent-primary)" : done ? "var(--green)" : BORDER}`,
                      color: active ? "#fff" : done ? "var(--green)" : "var(--text-muted)",
                      transition: "all 0.3s", flexShrink: 0,
                    }}>
                      {done ? "✓" : i + 1}
                    </div>
                    <span style={{
                      fontSize: "13px", fontWeight: active ? 700 : 500,
                      color: active ? "var(--text-primary)" : "var(--text-muted)",
                    }}>{s.title}</span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div style={{ flex: 1, height: "1px", margin: "0 12px", background: done ? "var(--green)" : BORDER, transition: "background 0.3s" }} />
                  )}
                </React.Fragment>
              );
            })}
          </div>

        {/* Step content */}
        <div key={step} className="question-enter" onKeyDown={(e) => { if (e.key === "Enter") goNext(); }}>
          {step === 0 && (
            <>
              <div style={fieldStyle}>
                <label style={labelStyle}>{t("Full Name")} *</label>
                <input type="text" value={form.name} onChange={set("name")} placeholder={t("e.g. Ravi Kumar")} style={inputStyle} autoFocus />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div style={fieldStyle}>
                  <label style={labelStyle}>{t("Age Group")} *</label>
                  <select value={form.age_group} onChange={set("age_group")} style={inputStyle}>
                    {AGE_GROUPS.map((a) => <option key={a}>{a}</option>)}
                  </select>
                </div>
                <div style={fieldStyle}>
                  <label style={labelStyle}>{t("Gender")}</label>
                  <select value={form.gender} onChange={set("gender")} style={inputStyle}>
                    <option value="">{t("Prefer not to say")}</option>
                    <option value="Male">{t("Male")}</option>
                    <option value="Female">{t("Female")}</option>
                    <option value="Other">{t("Other")}</option>
                  </select>
                </div>
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <div style={fieldStyle}>
                <label style={labelStyle}>{t("State / Region")} *</label>
                <select value={form.state} onChange={set("state")} style={inputStyle} autoFocus>
                  <option value="">{t("Select state…")}</option>
                  {STATES.map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div style={fieldStyle}>
                <label style={labelStyle}>{t("Occupation")} *</label>
                <select value={form.occupation} onChange={set("occupation")} style={inputStyle}>
                  <option value="">{t("Select occupation…")}</option>
                  {OCCUPATIONS.map((o) => <option key={o}>{o}</option>)}
                </select>
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)", lineHeight: 1.5 }}>
                {t("We use this to match you with schemes and guidance for your state and work.")}
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div style={fieldStyle}>
                  <label style={labelStyle}>{t("Preferred Language")}</label>
                  <select value={form.preferred_language} onChange={set("preferred_language")} style={inputStyle}>
                    {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
                  </select>
                </div>
                <div style={fieldStyle}>
                  <label style={labelStyle}>{t("Education Level")}</label>
                  <select value={form.education_level} onChange={set("education_level")} style={inputStyle}>
                    <option value="">{t("Select…")}</option>
                    {EDUCATION.map((e) => <option key={e}>{e}</option>)}
                  </select>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div style={fieldStyle}>
                  <label style={labelStyle}>{t("Has Smartphone?")}</label>
                  <select value={String(form.has_smartphone)} onChange={set("has_smartphone")} style={inputStyle}>
                    <option value="true">{t("Yes")}</option>
                    <option value="false">{t("No")}</option>
                  </select>
                </div>
                <div style={fieldStyle}>
                  <label style={labelStyle}>{t("Has Bank Account?")}</label>
                  <select
                    value={form.has_bank_account === null ? "" : String(form.has_bank_account)}
                    onChange={(e) => {
                      const v = e.target.value === "" ? null : e.target.value === "true";
                      setForm((p) => ({ ...p, has_bank_account: v }));
                    }}
                    style={inputStyle}
                  >
                    <option value="">{t("Not sure / prefer not to say")}</option>
                    <option value="true">{t("Yes")}</option>
                    <option value="false">{t("No")}</option>
                  </select>
                </div>
              </div>
            </>
          )}
        </div>

        {error && (
          <div style={{ color: "var(--red)", fontSize: "12px", marginTop: "6px", marginBottom: "10px" }}>
            {error}
          </div>
        )}

          {/* Footer nav */}
          <div style={{ display: "flex", gap: "12px", marginTop: "22px" }}>
            {step > 0 && (
              <button onClick={goBack} disabled={loading} style={{
                padding: "14px 26px", background: "transparent",
                border: `1px solid ${BORDER}`, borderRadius: "99px",
                color: "var(--text-secondary)", fontSize: "15px", fontWeight: 600,
                cursor: "pointer", fontFamily: "var(--font-sans)",
              }}>
                {t("Back")}
              </button>
            )}
            <button onClick={goNext} disabled={loading} style={{
              flex: 1, padding: "14px",
              background: loading ? "var(--agent-pending)" : "linear-gradient(135deg, var(--accent-primary), #9a4a2c)",
              border: "none", borderRadius: "99px", color: "#fff",
              fontSize: "15px", fontWeight: 700,
              cursor: loading ? "not-allowed" : "pointer", transition: "background 0.2s",
              fontFamily: "var(--font-sans)",
              boxShadow: loading ? "none" : "0 4px 16px rgba(184,92,56,0.3)",
            }}>
              {loading
                ? t("Saving…")
                : step < STEPS.length - 1
                  ? t("Continue")
                  : t("Save Profile & Start Assessment")}
            </button>
          </div>
        </div>

        {/* Trust badges — below the form */}
        <div style={{
          display: "flex", justifyContent: "center", flexWrap: "wrap",
          gap: "10px 22px", marginTop: "20px",
          fontSize: "13px", color: "var(--text-muted)",
        }}>
          <span>{t("Takes 2 minutes")}</span>
          <span>·</span>
          <span>{t("Your data stays private")}</span>
          <span>·</span>
          <span>{t("Any Indian language")}</span>
        </div>
      </div>
    </div>
  );
}
