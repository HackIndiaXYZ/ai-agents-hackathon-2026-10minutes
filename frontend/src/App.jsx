// App.jsx — Tab layout: Chat | Profile & Assessment

import React, { useState, useCallback, useEffect, useRef, useLayoutEffect } from "react";
import { useNavigate } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";
import ChatWindow from "./components/ChatWindow";
import AgentPipeline from "./components/AgentPipeline";
import ProfileSetup from "./components/ProfileSetup";
import OnboardingQuestionnaire from "./components/OnboardingQuestionnaire";
import KnowledgeTab from "./components/KnowledgeTab";
import BenefitsHub from "./components/BenefitsHub";
import RAGTestPage from "./components/RAGTestPage";
import ProfileSwitcher from "./components/ProfileSwitcher";
import DataLoopPanel from "./components/DataLoopPanel";
import { getAllProfiles, getKnowledgeGraph } from "./api/client";
import { useT, LanguageSwitcher } from "./i18n";
import "./index.css";

function newSessionId() { return uuidv4(); }

const INITIAL_AGENT_STATES = {};

// Warm border used across the chat surfaces
const BORDER = "rgba(61,43,31,0.14)";

// Completion-screen call-to-action card style
const ctaCard = (accent) => ({
  padding: "16px 14px", background: "var(--bg-card)",
  border: `1px solid var(--border-subtle)`, borderLeft: `3px solid ${accent}`,
  borderRadius: "var(--radius-md)", cursor: "pointer", textAlign: "left",
  transition: "all 0.2s",
});

// ── Session Inspector (collapsible left sidebar, chat tab only) ───────────────
const roundBtn = {
  display: "flex", alignItems: "center", justifyContent: "center",
  width: "34px", height: "34px", borderRadius: "99px", flexShrink: 0,
  background: "rgba(255,255,255,0.55)", border: `1px solid ${BORDER}`,
  color: "var(--text-secondary)", cursor: "pointer", fontSize: "18px",
  lineHeight: 1, transition: "all 0.2s",
};

const SessionInspector = ({ sessionData, sessionId, open, onToggle }) => {
  const [expanded, setExpanded] = useState({});
  const toggle = (key) => setExpanded((p) => ({ ...p, [key]: !p[key] }));

  // Collapsed rail — just a round toggle + vertical label
  if (!open) {
    return (
      <div style={{
        height: "100%", display: "flex", flexDirection: "column",
        alignItems: "center", paddingTop: "16px", gap: "16px",
      }}>
        <button onClick={onToggle} title="Expand session data" style={roundBtn}>›</button>
        <div style={{
          writingMode: "vertical-rl", transform: "rotate(180deg)",
          fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)",
          letterSpacing: "0.06em",
        }}>
          Session Data
        </div>
      </div>
    );
  }

  const Section = ({ title, children, badge }) => (
    <div style={{ marginBottom: "12px" }}>
      <div
        onClick={() => toggle(title)}
        style={{
          display: "flex", alignItems: "center", gap: "8px",
          cursor: "pointer", padding: "11px 14px",
          borderRadius: "14px", background: "rgba(255,255,255,0.5)",
          border: `1px solid ${BORDER}`,
          transition: "background 0.2s",
        }}
      >
        <span style={{ fontSize: "14px", fontWeight: 600, flex: 1, color: "var(--text-primary)" }}>{title}</span>
        {badge && (
          <span style={{
            fontSize: "10px", padding: "2px 8px", borderRadius: "99px",
            background: "rgba(184,92,56,0.14)", color: "var(--accent-primary)",
            border: `1px solid ${BORDER}`, fontWeight: 700,
          }}>{badge}</span>
        )}
        <span style={{ color: "var(--text-muted)", fontSize: "16px", fontWeight: 400 }}>
          {expanded[title] ? "−" : "+"}
        </span>
      </div>
      {expanded[title] && (
        <div className="animate-fade-in" style={{
          marginTop: "6px", padding: "13px", borderRadius: "14px",
          background: "rgba(255,255,255,0.35)", border: `1px solid ${BORDER}`,
          fontSize: "13px", color: "var(--text-secondary)", overflow: "auto",
          maxHeight: "240px",
        }}>
          {children}
        </div>
      )}
    </div>
  );

  const ProfileField = ({ label, value }) => (
    <div style={{ display: "flex", gap: "8px", marginBottom: "6px" }}>
      <span style={{ color: "var(--text-muted)", minWidth: "130px" }}>{label}:</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>
        {value !== undefined && value !== null ? String(value) : "—"}
      </span>
    </div>
  );

  return (
    <div style={{ padding: "16px", overflowY: "auto", height: "100%" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px",
        paddingBottom: "14px", borderBottom: `1px solid ${BORDER}`,
      }}>
        <button onClick={onToggle} title="Collapse" style={roundBtn}>‹</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>Session Data</div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {sessionId.slice(0, 12)}…
          </div>
        </div>
      </div>

      {!sessionData ? (
        <div style={{
          color: "var(--text-muted)", fontSize: "14px", textAlign: "center",
          padding: "30px 14px", lineHeight: 1.7,
        }}>
          Session data will appear after your first message.
        </div>
      ) : (
        <>
          <Section title="Language Detection" badge={sessionData.detected_language}>
            <ProfileField label="Language" value={sessionData.detected_language} />
            <ProfileField label="Script" value={sessionData.detected_script} />
            <ProfileField label="Confidence" value={`${Math.round((sessionData.confidence_score || 0) * 100)}%`} />
          </Section>

          <Section title="User Profile" badge={Object.keys(sessionData.user_profile || {}).length + " fields"}>
            {Object.entries(sessionData.user_profile || {}).length === 0 ? (
              <div style={{ color: "var(--text-muted)" }}>No profile data yet.</div>
            ) : (
              Object.entries(sessionData.user_profile).map(([k, v]) => (
                <ProfileField key={k} label={k.replace(/_/g, " ")} value={Array.isArray(v) ? v.join(", ") : typeof v === "object" ? JSON.stringify(v) : v} />
              ))
            )}
          </Section>

          <Section title="Sub-queries" badge={`${(sessionData.sub_queries || []).length}`}>
            {(sessionData.sub_queries || []).map((sq, i) => (
              <div key={i} style={{
                marginBottom: "8px", padding: "9px 11px",
                background: "rgba(255,255,255,0.5)", borderRadius: "12px",
                border: `1px solid ${BORDER}`,
              }}>
                <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "3px" }}>{sq.query}</div>
                <div style={{ display: "flex", gap: "7px" }}>
                  <span style={{ color: "var(--accent-primary)" }}>{sq.type}</span>
                  {sq.requires_web_search && (
                    <span style={{ color: "var(--amber)", fontSize: "12px" }}>web</span>
                  )}
                  <span style={{ color: "var(--text-muted)" }}>{sq.status}</span>
                </div>
              </div>
            ))}
            {!(sessionData.sub_queries || []).length && (
              <div style={{ color: "var(--text-muted)" }}>No sub-queries yet.</div>
            )}
          </Section>

          {(sessionData.fraud_flags || []).length > 0 && (
            <Section title="Safety Flags" badge={sessionData.fraud_flags.length}>
              {sessionData.fraud_flags.map((f, i) => (
                <div key={i} style={{ color: "var(--red)", marginBottom: "4px" }}>• {f}</div>
              ))}
            </Section>
          )}

          <Section title="Agent Trace" badge={`${(sessionData.agent_trace || []).length} agents`}>
            <pre style={{
              fontFamily: "var(--font-mono)", fontSize: "12px",
              color: "var(--text-secondary)", whiteSpace: "pre-wrap", wordBreak: "break-all",
            }}>
              {JSON.stringify(sessionData.agent_trace, null, 2)}
            </pre>
          </Section>

          {(sessionData.errors || []).length > 0 && (
            <Section title="Errors" badge={sessionData.errors.length}>
              {sessionData.errors.map((e, i) => (
                <div key={i} style={{ color: "var(--red)", marginBottom: "4px", fontSize: "12px" }}>{e}</div>
              ))}
            </Section>
          )}
        </>
      )}
    </div>
  );
};

// ── Onboarding tab content ────────────────────────────────────────────────────
const OnboardingTab = ({ activeProfile, onProfileReady, onViewKnowledge }) => {
  const t = useT();
  const [step, setStep] = useState("profile"); // "profile" | "survey" | "done"
  const [profile, setProfile] = useState(activeProfile);
  const [kg, setKg] = useState(null);
  const [existingProfiles, setExistingProfiles] = useState([]);

  useEffect(() => {
    getAllProfiles().then(setExistingProfiles).catch(() => {});
  }, []);

  // If profile already finished onboarding, jump to the completion screen
  useEffect(() => {
    if (activeProfile?.profile_id && activeProfile?.onboarding_complete) {
      setProfile(activeProfile);
      getKnowledgeGraph(activeProfile.profile_id)
        .then((data) => { if (data) { setKg(data); setStep("done"); } })
        .catch(() => {});
    }
  }, [activeProfile]);

  const handleProfileCreated = (p) => {
    setProfile(p);
    if (p.onboarding_complete) {
      getKnowledgeGraph(p.profile_id)
        .then((data) => { if (data) setKg(data); })
        .catch(() => {});
      setStep("done");
    } else {
      setStep("survey");
    }
  };

  const handleSurveyComplete = (kgData) => {
    setKg(kgData);
    setStep("done");
  };

  // Step indicator
  const steps = [
    { id: "profile", label: t("Profile") },
    { id: "survey",  label: t("Assessment") },
    { id: "done",    label: t("Done") },
  ];

  // Macro step indicator (Profile → Assessment → Done), rendered under the form
  const StepIndicator = () => (
    <div style={{
      maxWidth: "560px", margin: "40px auto 0",
      display: "flex", alignItems: "center",
      paddingTop: "24px", borderTop: "1px solid rgba(61,43,31,0.14)",
    }}>
      {steps.map((s, i) => {
        const isDone = steps.indexOf(steps.find((x) => x.id === step)) > i;
        const isActive = s.id === step;
        return (
          <React.Fragment key={s.id}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{
                width: "30px", height: "30px", borderRadius: "50%",
                display: "flex", alignItems: "center", justifyContent: "center",
                background: isActive ? "var(--accent-primary)" : isDone ? "var(--green-dim)" : "rgba(255,255,255,0.6)",
                border: `1px solid ${isActive ? "var(--accent-primary)" : isDone ? "var(--green)" : "rgba(61,43,31,0.14)"}`,
                fontSize: "13px",
                color: isActive ? "#fff" : isDone ? "var(--green)" : "var(--text-muted)",
                fontWeight: 700,
                transition: "all 0.3s", flexShrink: 0,
              }}>
                {isDone ? "✓" : i + 1}
              </div>
              <span style={{
                fontSize: "13px", fontWeight: isActive ? 700 : 500,
                color: isActive ? "var(--text-primary)" : "var(--text-muted)",
              }}>
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div style={{
                flex: 1, height: "1px", margin: "0 12px",
                background: isDone ? "var(--green)" : "rgba(61,43,31,0.14)",
                transition: "background 0.3s",
              }} />
            )}
          </React.Fragment>
        );
      })}

      {/* Reset button */}
      {step !== "profile" && (
        <button
          onClick={() => { setStep("profile"); setKg(null); }}
          style={{
            marginLeft: "16px",
            padding: "7px 16px",
            background: "transparent",
            border: "1px solid rgba(61,43,31,0.14)",
            borderRadius: "99px",
            color: "var(--text-muted)",
            fontSize: "12px",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          {t("New Profile")}
        </button>
      )}
    </div>
  );

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Step content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 24px 24px" }}>
        {step === "profile" && (
          <ProfileSetup
            onProfileCreated={handleProfileCreated}
            existingProfiles={existingProfiles}
          />
        )}
        {step === "survey" && profile && (
          <OnboardingQuestionnaire
            profile={profile}
            onComplete={handleSurveyComplete}
          />
        )}
        {step === "done" && profile && (
          <div className="animate-scale-in" style={{ maxWidth: "520px", margin: "0 auto", paddingTop: "40px", textAlign: "center" }}>
            <div style={{ fontSize: "52px", marginBottom: "12px", filter: "drop-shadow(0 0 24px rgba(16,185,129,0.4))" }}>🎉</div>
            <div style={{ fontSize: "20px", fontWeight: 700, marginBottom: "8px" }}>
              {t("You're all set,")} {profile.name}!
            </div>
            <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "8px" }}>
              {t("We've built your personal knowledge graph")}
              {kg && (
                <> — {t("you're at")}{" "}
                  <strong style={{ color: "var(--accent-secondary)" }}>
                    {Math.round((kg.overall_score || 0) * 100)}% {t("overall")}
                  </strong>{" "}
                  ({kg.literacy_level})
                </>
              )}. {t("Everything is now personalised to you.")}
            </div>

            <div style={{
              display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px",
              marginTop: "24px", textAlign: "left",
            }}>
              <button onClick={() => onViewKnowledge(profile, kg)} style={ctaCard("var(--accent-primary)")}>
                <div style={{ fontSize: "22px", marginBottom: "6px" }}>🧠</div>
                <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>{t("View My Knowledge")}</div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{t("Graph + progress dashboard")}</div>
              </button>
              <button onClick={() => onProfileReady(profile)} style={ctaCard("var(--green)")}>
                <div style={{ fontSize: "22px", marginBottom: "6px" }}>💬</div>
                <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>{t("Start Chatting")}</div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{t("Ask anything, in any language")}</div>
              </button>
            </div>
          </div>
        )}

        <StepIndicator />
      </div>
    </div>
  );
};

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const t = useT();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("onboarding");
  const [sessionId, setSessionId] = useState(newSessionId);
  const [messages, setMessages] = useState([]);
  const [agentStates, setAgentStates] = useState(INITIAL_AGENT_STATES);
  const [sessionData, setSessionData] = useState(null);
  const [currentRunningAgent, setCurrentRunningAgent] = useState(null);
  const [activeProfile, setActiveProfile] = useState(null);
  const [activeKg, setActiveKg] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [inspectorOpen, setInspectorOpen] = useState(true);

  const refreshProfiles = useCallback(() => {
    getAllProfiles().then(setProfiles).catch(() => {});
  }, []);

  useEffect(() => { refreshProfiles(); }, [refreshProfiles]);

  const handleAgentEvent = useCallback((data) => {
    if (data.event === "stream_start") {
      setAgentStates({});
      setCurrentRunningAgent("language");
      return;
    }
    if (data.event === "agent_complete") {
      const { agent, latency_ms, errors = [] } = data;
      setAgentStates((prev) => ({
        ...prev,
        [agent]: { status: errors.length > 0 ? "error" : "done", latencyMs: latency_ms },
      }));
      const PIPELINE = ["language","context","supervisor","clarification","decomposition","web_search","reasoning","recommendation","fraud_safety","formatter","feedback"];
      const idx = PIPELINE.indexOf(agent);
      if (idx >= 0 && idx < PIPELINE.length - 1) {
        const next = PIPELINE[idx + 1];
        setCurrentRunningAgent(next);
        setAgentStates((prev) => ({ ...prev, [next]: { status: "running" } }));
      }
    }
    if (data.event === "final_response") {
      setCurrentRunningAgent(null);
      setSessionData({
        detected_language: data.detected_language || "English",
        detected_script: "—",
        confidence_score: data.confidence || 0,
        user_profile: data.user_profile || {},
        sub_queries: data.sub_queries || [],
        fraud_flags: data.fraud_flags || [],
        safety_blocks_applied: (data.fraud_flags || []).length > 0,
        agent_trace: (data.agents_fired || []).map((a) => ({
          agent: a,
          latency_ms: agentStates[a]?.latencyMs ?? 0,
        })),
        errors: [],
      });
    }
  }, [agentStates]);

  const handleNewMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const handleReset = useCallback(() => {
    setSessionId(newSessionId());
    setMessages([]);
    setAgentStates({});
    setSessionData(null);
    setCurrentRunningAgent(null);
  }, []);

  const handleProfileReady = useCallback((profile) => {
    setActiveProfile(profile);
    refreshProfiles();
    setActiveTab("chat");
  }, [refreshProfiles]);

  const handleViewKnowledge = useCallback((profile, kg) => {
    setActiveProfile(profile);
    if (kg) setActiveKg(kg);
    setActiveTab("knowledge");
  }, []);

  // Switch the active profile from the top-bar dropdown (load its KG too).
  const handleSelectProfile = useCallback((profile) => {
    setActiveProfile(profile);
    setActiveKg(null);
    getKnowledgeGraph(profile.profile_id).then((kg) => { if (kg) setActiveKg(kg); }).catch(() => {});
  }, []);

  const glassTabStyle = (tab) => ({
    position: "relative",
    zIndex: 1,
    padding: "8px 16px",
    borderRadius: "99px",
    background: "transparent",
    border: "none",
    color: activeTab === tab ? "#3D2B1F" : "rgba(61,43,31,0.55)",
    fontSize: "13px",
    fontWeight: activeTab === tab ? 600 : 500,
    cursor: "pointer",
    transition: "color 0.25s",
    fontFamily: '"Google Sans Flex", sans-serif',
    whiteSpace: "nowrap",
    display: "flex",
    alignItems: "center",
    gap: "6px",
  });

  const tabs = [
    { id: "onboarding", label: t("Profile & Assessment") },
    { id: "knowledge",  label: t("Knowledge") },
    { id: "chat",       label: t("Chat") },
    { id: "benefits",   label: t("Benefits & Help") },
    { id: "dataloop",   label: t("Data Loop") },
    { id: "rag",        label: t("RAG Test") },
  ];

  // Sliding glass highlight (iPhone-camera-style) — track the active tab's box.
  const tabBtnRefs = useRef({});
  const [tabPill, setTabPill] = useState({ left: 0, width: 0 });
  const activeLabel = tabs.find((tb) => tb.id === activeTab)?.label;
  useLayoutEffect(() => {
    const measure = () => {
      const el = tabBtnRefs.current[activeTab];
      if (el) setTabPill({ left: el.offsetLeft, width: el.offsetWidth });
    };
    measure();
    // re-measure once fonts settle (label widths shift after webfont loads)
    const id = setTimeout(measure, 250);
    window.addEventListener("resize", measure);
    return () => { clearTimeout(id); window.removeEventListener("resize", measure); };
  }, [activeTab, activeLabel]);

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100vh",
      background: "#ECD8C4",
      fontFamily: '"Google Sans Flex", sans-serif',
    }}>
      {/* ── Navbar: plain cream bar, glass highlight slides between tabs ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        gap: "16px", padding: "14px 24px", flexShrink: 0, zIndex: 10,
      }}>
        {/* Left — Logo (text only) */}
        <div
          onClick={() => navigate("/")}
          title={t("Back to home")}
          style={{ display: "flex", alignItems: "baseline", gap: "5px", cursor: "pointer", flexShrink: 0 }}
        >
          <span style={{ fontSize: "18px", fontWeight: 700, color: "#3D2B1F", letterSpacing: "-0.01em" }}>
            Sahayak
          </span>
          <span style={{ fontSize: "18px", fontWeight: 500, color: "#B85C38" }}>
            AI
          </span>
        </div>

        {/* Middle — tab scroller with sliding glass pill */}
        <div style={{
          position: "relative",
          display: "flex", alignItems: "center", gap: "2px",
          padding: "4px", overflowX: "auto", maxWidth: "100%",
        }}>
          {/* the glass "scroller" highlight */}
          <div style={{
            position: "absolute", top: "4px", bottom: "4px",
            left: `${tabPill.left}px`, width: `${tabPill.width}px`,
            borderRadius: "99px",
            background: "rgba(255,255,255,0.55)",
            WebkitBackdropFilter: "blur(12px) saturate(1.6)",
            backdropFilter: "blur(12px) saturate(1.6)",
            boxShadow: "0 2px 10px rgba(61,43,31,0.12), inset 0 1px 0 rgba(255,255,255,0.7)",
            transition: "left 1.1s cubic-bezier(0.22,1,0.36,1), width 1.1s cubic-bezier(0.22,1,0.36,1)",
            pointerEvents: "none", zIndex: 0,
          }} />
          {tabs.map((tb) => (
            <button
              key={tb.id}
              ref={(el) => { tabBtnRefs.current[tb.id] = el; }}
              style={glassTabStyle(tb.id)}
              onClick={() => setActiveTab(tb.id)}
            >
              {tb.label}
              {tb.id === "chat" && activeProfile && (
                <span style={{
                  fontSize: "10px", padding: "1px 7px", borderRadius: "99px",
                  background: "rgba(16,133,89,0.16)", color: "#0f7a4f",
                  fontWeight: 700,
                }}>
                  {activeProfile.name}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Right — profile + language */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexShrink: 0 }}>
          <LanguageSwitcher theme="light" />
          <ProfileSwitcher
            theme="light"
            profiles={profiles}
            activeProfile={activeProfile}
            onSelect={handleSelectProfile}
            onNew={() => setActiveTab("onboarding")}
          />
        </div>
      </div>

      {/* ── Tab content ── */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
        {activeTab === "onboarding" ? (
          <div style={{ flex: 1, overflow: "hidden" }}>
            <OnboardingTab
              activeProfile={activeProfile}
              onProfileReady={handleProfileReady}
              onViewKnowledge={handleViewKnowledge}
            />
          </div>
        ) : activeTab === "knowledge" ? (
          <div style={{ flex: 1, overflowY: "auto", padding: "0 24px" }}>
            <KnowledgeTab
              profile={activeProfile}
              kg={activeKg}
              onGoToProfile={() => setActiveTab("onboarding")}
            />
          </div>
        ) : activeTab === "benefits" ? (
          <div style={{ flex: 1, overflowY: "auto", padding: "0 24px" }}>
            <BenefitsHub
              profile={activeProfile}
              onGoToProfile={() => setActiveTab("onboarding")}
            />
          </div>
        ) : activeTab === "dataloop" ? (
          <div style={{ flex: 1, overflowY: "auto", padding: "0 24px" }}>
            <DataLoopPanel />
          </div>
        ) : activeTab === "rag" ? (
          <div style={{ flex: 1, overflow: "hidden" }}>
            <RAGTestPage />
          </div>
        ) : (
          /* Chat tab: three-panel layout — Session Data | Chat | Pipeline */
          <div style={{ flex: 1, display: "flex", overflow: "hidden", padding: "12px", gap: "12px" }}>
            {/* Left: Session Data sidebar (collapsible) */}
            <div style={{
              width: inspectorOpen ? "320px" : "56px", flexShrink: 0,
              overflowY: "auto", overflowX: "hidden",
              background: "rgba(255,255,255,0.32)",
              border: `1px solid ${BORDER}`, borderRadius: "20px",
              transition: "width 0.3s cubic-bezier(0.22,1,0.36,1)",
            }}>
              <SessionInspector
                sessionData={sessionData}
                sessionId={sessionId}
                open={inspectorOpen}
                onToggle={() => setInspectorOpen((o) => !o)}
              />
            </div>

            {/* Center: Chat */}
            <div style={{
              flex: "1.8", minWidth: 0, display: "flex", flexDirection: "column",
              background: "rgba(255,255,255,0.22)",
              border: `1px solid ${BORDER}`, borderRadius: "20px", overflow: "hidden",
            }}>
              <ChatWindow
                sessionId={sessionId}
                onAgentEvent={handleAgentEvent}
                onNewMessage={handleNewMessage}
                onReset={handleReset}
                messages={messages}
                activeProfile={activeProfile}
              />
            </div>

            {/* Right: Agent Pipeline */}
            <div style={{
              width: "300px", flexShrink: 0, overflowY: "auto",
              background: "rgba(255,255,255,0.32)",
              border: `1px solid ${BORDER}`, borderRadius: "20px",
            }}>
              <AgentPipeline agentStates={agentStates} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
