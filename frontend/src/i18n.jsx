// i18n.jsx — AI-powered, on-demand UI translation.
//
// Components wrap visible strings in t("English text"). The English text IS the
// key, so the fallback is automatic. When the user picks another language, all
// strings seen so far are batch-sent to the backend (/i18n/translate, Gemini +
// Redis cache) and the returned translations are cached in localStorage.
//
// Strings register themselves as they render, so screens visited later are
// translated automatically without any central string catalog to maintain.

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback,
} from "react";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// Module-level set of every string ever passed to t() this session.
const registry = new Set();

const I18nContext = createContext({
  lang: "English",
  setLang: () => {},
  t: (s) => s,
  loading: false,
});

export const LANGUAGES = [
  "English",
  "Hindi",
  "Bengali",
  "Telugu",
  "Marathi",
  "Tamil",
  "Gujarati",
  "Kannada",
  "Malayalam",
  "Punjabi",
  "Odia",
  "Urdu",
];

export function useT() {
  return useContext(I18nContext).t;
}
export function useLang() {
  const { lang, setLang, loading } = useContext(I18nContext);
  return { lang, setLang, loading };
}

function loadDict(lang) {
  try {
    return JSON.parse(localStorage.getItem(`ui_dict_${lang}`) || "{}");
  } catch {
    return {};
  }
}
function saveDict(lang, dict) {
  try {
    localStorage.setItem(`ui_dict_${lang}`, JSON.stringify(dict));
  } catch {
    /* storage full / disabled — ignore */
  }
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(
    () => localStorage.getItem("ui_lang") || "English",
  );
  const [dict, setDict] = useState(() =>
    lang === "English" ? {} : loadDict(lang),
  );
  const [loading, setLoading] = useState(false);

  const dictRef = useRef(dict);
  dictRef.current = dict;
  const langRef = useRef(lang);
  langRef.current = lang;
  const syncingRef = useRef(false);
  const timerRef = useRef(null);

  const setLang = useCallback((l) => {
    try {
      localStorage.setItem("ui_lang", l);
    } catch {
      /* ignore */
    }
    setLangState(l);
    setDict(l === "English" ? {} : loadDict(l));
  }, []);

  const t = useCallback((s) => {
    if (typeof s !== "string" || !s) return s;
    registry.add(s);
    if (langRef.current === "English") return s;
    return dictRef.current[s] ?? s; // fall back to English until translated
  }, []);

  const sync = useCallback(async () => {
    const curLang = langRef.current;
    if (curLang === "English" || syncingRef.current) return;

    const missing = [];
    for (const s of registry) if (!(s in dictRef.current)) missing.push(s);
    if (!missing.length) return;

    syncingRef.current = true;
    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/i18n/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lang: curLang, strings: missing }),
      });
      if (res.ok && langRef.current === curLang) {
        const data = await res.json();
        const merged = { ...dictRef.current, ...(data.translations || {}) };
        // Mark any still-missing strings as identity so we don't re-request them
        for (const m of missing) if (!(m in merged)) merged[m] = m;
        dictRef.current = merged;
        setDict(merged);
        saveDict(curLang, merged);
      }
    } catch {
      /* network error — keep showing English */
    } finally {
      syncingRef.current = false;
      setLoading(false);
    }
  }, []);

  // After each render, debounce-sync any newly-registered strings.
  useEffect(() => {
    if (lang === "English") return undefined;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(sync, 350);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  });

  return (
    <I18nContext.Provider value={{ lang, setLang, t, loading }}>
      {children}
    </I18nContext.Provider>
  );
}

// Dropdown for the top bar.
export function LanguageSwitcher({ theme = "dark" }) {
  const { lang, setLang, loading } = useLang();
  const light = theme === "light";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
      <select
        value={lang}
        onChange={(e) => setLang(e.target.value)}
        title="Interface language"
        style={
          light
            ? {
                background: "rgba(255,255,255,0.35)",
                border: "1px solid rgba(61,43,31,0.2)",
                color: "#3D2B1F",
                borderRadius: "99px",
                padding: "6px 10px",
                fontSize: "12px",
                cursor: "pointer",
                outline: "none",
                fontFamily: '"Google Sans Flex", sans-serif',
                fontWeight: 500,
              }
            : {
                background: "var(--bg-input)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-secondary)",
                borderRadius: "7px",
                padding: "5px 8px",
                fontSize: "12px",
                cursor: "pointer",
                outline: "none",
              }
        }
      >
        {LANGUAGES.map((l) => (
          <option key={l} value={l}>
            {l}
          </option>
        ))}
      </select>
    </div>
  );
}
