// api/client.js — API and SSE client for the Financial Inclusion Assistant

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

/**
 * Open an SSE stream to /chat.
 * Calls onEvent(eventData) for each parsed SSE event.
 * Calls onDone() when the stream closes.
 * Calls onError(err) on failure.
 * Returns a cleanup function that closes the fetch abort controller.
 */
export function streamChat({ sessionId, message, languageHint, profileId, onEvent, onDone, onError }) {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message,
          language_hint: languageHint || null,
          profile_id: profileId || null,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const text = await response.text();
        onError(new Error(`HTTP ${response.status}: ${text}`));
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // last incomplete line stays in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch {
              // malformed JSON line — skip
            }
          }
        }
      }

      onDone();
    } catch (err) {
      if (err.name !== "AbortError") {
        onError(err);
      }
    }
  })();

  return () => controller.abort();
}

/**
 * Submit thumbs-up/down feedback for a turn.
 */
export async function submitFeedback({ sessionId, turnNumber, rating }) {
  const response = await fetch(`${BASE_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      turn_number: turnNumber,
      rating,
    }),
  });
  return response.json();
}

/**
 * Fetch full session debug state.
 */
export async function getSession(sessionId) {
  const response = await fetch(`${BASE_URL}/session/${sessionId}`);
  if (!response.ok) return null;
  return response.json();
}

/**
 * Health check.
 */
export async function healthCheck() {
  try {
    const response = await fetch(`${BASE_URL}/health`);
    return response.json();
  } catch {
    return { status: "error", redis_connected: false };
  }
}

// ── Profile & Onboarding API ──────────────────────────────────────────────────

export async function createProfile(profileData) {
  const res = await fetch(`${BASE_URL}/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profileData),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getProfile(profileId) {
  const res = await fetch(`${BASE_URL}/profile/${profileId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getAllProfiles() {
  const res = await fetch(`${BASE_URL}/profiles`);
  if (!res.ok) return [];
  return res.json();
}

export async function getNextQuestion(profileId, answers, questionNumber) {
  const res = await fetch(`${BASE_URL}/onboarding/next-question`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile_id: profileId,
      answers,
      question_number: questionNumber,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function completeOnboarding(profileId, answers) {
  const res = await fetch(`${BASE_URL}/onboarding/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_id: profileId, answers }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getKnowledgeGraph(profileId) {
  const res = await fetch(`${BASE_URL}/knowledge-graph/${profileId}`);
  if (!res.ok) return null;
  return res.json();
}

// ── BGE-M3 / Qdrant RAG ───────────────────────────────────────────────────────

/**
 * Search for similar fraud cases using BGE-M3 hybrid retrieval + Gemini synthesis.
 * @param {string} query  - User's query in any language
 * @param {number} topK   - Number of similar questions to return (default 5)
 */
export async function searchRAG(query, topK = 5) {
  const res = await fetch(`${BASE_URL}/rag/similar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Check if Qdrant is running and the collection is indexed.
 */
export async function ragHealth() {
  try {
    const res = await fetch(`${BASE_URL}/rag/health`);
    return res.json();
  } catch {
    return { qdrant_healthy: false };
  }
}

// ── Financial-inclusion features ──────────────────────────────────────────────

async function _postJSON(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Scheme Eligibility Engine — ranked schemes the user qualifies for. */
export async function getEligibleSchemes(profileId, language) {
  return _postJSON("/features/schemes/eligibility", {
    profile_id: profileId,
    language: language || null,
  });
}

/** Document Checklist Generator. */
export async function getDocumentChecklist({ schemeOrService, profileId, state, language }) {
  return _postJSON("/features/documents/checklist", {
    scheme_or_service: schemeOrService,
    profile_id: profileId || null,
    state: state || null,
    language: language || null,
  });
}

/** Guided Complaint Filing. */
export async function getComplaintGuide({ issue, profileId, state, language }) {
  return _postJSON("/features/complaints/guide", {
    issue,
    profile_id: profileId || null,
    state: state || null,
    language: language || null,
  });
}

/** Live Fraud Alert Feed (Google News RSS). */
export async function getFraudAlerts({ state, profileId, limit = 10, language } = {}) {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  if (profileId) params.set("profile_id", profileId);
  if (language) params.set("language", language);
  params.set("limit", String(limit));
  const res = await fetch(`${BASE_URL}/features/fraud-alerts?${params.toString()}`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Adaptive data loop ────────────────────────────────────────────────────────

/** Queue + staging counts for the adaptive data loop. */
export async function getAdaptiveStats() {
  const res = await fetch(`${BASE_URL}/adaptive/stats`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Anonymise + format queued interactions into the staging dataset. */
export async function harvestAdaptive(maxEvents = 200) {
  return _postJSON("/adaptive/harvest", { max_events: maxEvents, batch_size: 8 });
}

/** Preview the last N anonymised staged rows. */
export async function previewAdaptive(limit = 10) {
  const res = await fetch(`${BASE_URL}/adaptive/preview?limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Promote the staging dataset into Qdrant (manual publish step). */
export async function ingestAdaptive() {
  const res = await fetch(`${BASE_URL}/adaptive/ingest`, { method: "POST" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Literacy Progress Dashboard. */
export async function getLiteracyProgress(profileId, language) {
  const params = new URLSearchParams();
  if (language) params.set("language", language);
  const qs = params.toString();
  const res = await fetch(`${BASE_URL}/features/literacy/progress/${profileId}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
