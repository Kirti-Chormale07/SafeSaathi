"use client";
import { useEffect, useRef, useState } from "react";
import Header from "@/components/Header";
import RiskCard from "@/components/RiskCard";
import VoiceRecorder from "@/components/VoiceRecorder";
import { analyzeScreenshot, analyzeText, analyzeVoice, fetchSamples } from "@/lib/api";
import { makeT } from "@/lib/i18n";

export default function Home() {
  const [lang, setLang] = useState("en");
  const t = makeT(lang);
  const [tab, setTab] = useState("text");

  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [samples, setSamples] = useState(null);
  const fileRef = useRef(null);

  useEffect(() => {
    fetchSamples().then(setSamples).catch(() => setSamples({}));
  }, []);

  async function run(fn) {
    setError("");
    setResult(null);
    setLoading(true);
    try {
      setResult(await fn());
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const doText = () => (text.trim() ? run(() => analyzeText(text.trim(), lang)) : setError(t("empty_input")));
  const doFile = () => (file ? run(() => analyzeScreenshot(file, lang)) : setError(t("empty_input")));
  const doVoice = (blob) => run(() => analyzeVoice(blob, lang));

  function pickSample(key) {
    const s = samples?.[key];
    if (!s) return;
    setTab("text");
    setText(s.text);
    run(() => analyzeText(s.text, lang));
  }

  function onPickFile(f) {
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : "");
  }

  function reset() {
    setResult(null);
    setError("");
    setText("");
    setFile(null);
    setPreview("");
    if (fileRef.current) fileRef.current.value = "";
  }

  const sampleKeys = samples ? Object.keys(samples) : [];

  return (
    <>
      <Header t={t} lang={lang} setLang={setLang} />

      <main className="shell">
        {result ? (
          <RiskCard result={result} t={t} lang={lang} onReset={reset} />
        ) : (
          <>
            {/* ---- mode tabs ---- */}
            <div className="tabs">
              {[
                { id: "text", icon: "💬", label: t("tab_text") },
                { id: "image", icon: "🖼️", label: t("tab_image") },
                { id: "voice", icon: "🎙️", label: t("tab_voice") },
              ].map((x) => (
                <button
                  key={x.id}
                  className={`tab ${tab === x.id ? "active" : ""}`}
                  onClick={() => setTab(x.id)}
                  type="button"
                >
                  <span className="icon">{x.icon}</span>
                  {x.label}
                </button>
              ))}
            </div>

            {error && <div className="alert-error">⚠️ {error}</div>}

            {/* ---- text mode ---- */}
            {tab === "text" && (
              <div className="card">
                <textarea
                  className="input"
                  placeholder={t("placeholder")}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  maxLength={4000}
                />
                <div style={{ marginTop: 12 }}>
                  <button className="btn btn-primary" onClick={doText} disabled={loading}>
                    {loading ? <><span className="spinner" /> {t("analyzing")}</> : <>🔍 {t("analyze")}</>}
                  </button>
                </div>
              </div>
            )}

            {/* ---- screenshot mode ---- */}
            {tab === "image" && (
              <div className="card">
                <p className="muted">{t("upload_hint")}</p>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={(e) => onPickFile(e.target.files?.[0] || null)}
                  style={{ fontSize: 16, width: "100%" }}
                />
                {preview && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={preview}
                    alt="Selected screenshot"
                    style={{ width: "100%", borderRadius: 12, marginTop: 10, border: "1px solid #e2e8f0" }}
                  />
                )}
                <div style={{ marginTop: 12 }}>
                  <button className="btn btn-primary" onClick={doFile} disabled={loading || !file}>
                    {loading ? <><span className="spinner" /> {t("analyzing")}</> : <>📤 {t("upload_btn")}</>}
                  </button>
                </div>
              </div>
            )}

            {/* ---- voice mode ---- */}
            {tab === "voice" && (
              <>
                <VoiceRecorder t={t} onComplete={doVoice} disabled={loading} />
                {loading && (
                  <div className="card" style={{ textAlign: "center" }}>
                    <span className="spinner" style={{ borderTopColor: "#0f766e" }} />
                    <p className="muted">Transcribing & checking...</p>
                  </div>
                )}
              </>
            )}

            {/* ---- samples ---- */}
            {sampleKeys.length > 0 && !loading && (
              <div className="card">
                <div className="section-title" style={{ marginTop: 0 }}>🎬 {t("samples")}</div>
                <div className="chips">
                  {sampleKeys.map((k) => (
                    <button key={k} className="chip" onClick={() => pickSample(k)} type="button">
                      {samples[k].label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>ℹ️ How SafeSaathi helps</div>
              <ul className="list">
                <li><span className="mark step">1.</span> Paste a message, upload a screenshot or record a call.</li>
                <li><span className="mark step">2.</span> Get a risk score with a plain-language reason.</li>
                <li><span className="mark step">3.</span> Hear the warning in Hindi, Marathi or English.</li>
                <li><span className="mark step">4.</span> One tap alerts your family and dials 1930.</li>
              </ul>
            </div>
          </>
        )}
      </main>
    </>
  );
}
