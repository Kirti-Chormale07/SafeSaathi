"use client";
import { useState } from "react";
import { alertGuardian, speak } from "@/lib/api";

/** Full analysis result: score hero, red flags, playbook, next steps, actions. */
export default function RiskCard({ result, t, lang, onReset }) {
  const a = result.analysis;
  const [speaking, setSpeaking] = useState(false);
  const [audioErr, setAudioErr] = useState("");
  const [guardian, setGuardian] = useState(null);

  const labelKey = a.risk_label; // safe | suspicious | scam
  const explanation = a.explanation;

  async function playWarning() {
    setAudioErr("");
    setSpeaking(true);
    try {
      const text = a.spoken_warning?.[lang] || a.spoken_warning?.en;
      const { audio_url } = await speak(text, lang);
      const audio = new Audio(audio_url);
      audio.onended = () => setSpeaking(false);
      audio.onerror = () => setSpeaking(false);
      await audio.play();
    } catch (e) {
      setSpeaking(false);
      setAudioErr(e.message || "Voice unavailable");
    }
  }

  async function sendGuardian() {
    const message =
      `SafeSaathi ${a.risk_label === "scam" ? "ALERT" : "check"}: ${a.risk_label.toUpperCase()} (${a.risk_score}/100) - ` +
      `${a.category}\n${a.explanation}\nMessage: "${(result.input.original || "").slice(0, 160)}"\n` +
      `Please call me. Report cyber fraud on 1930 / cybercrime.gov.in`;
    try {
      const res = await alertGuardian(message, a.risk_label);
      setGuardian(res);
      if (res.link) window.open(res.link, "_blank", "noopener");
    } catch (e) {
      setGuardian({ status: "error", note: e.message });
    }
  }

  return (
    <div>
      {/* ---- hero ---- */}
      <div className={`risk-hero ${labelKey}`}>
        <div className="risk-score">{a.risk_score}</div>
        <div>
          <div className="risk-label">{t(labelKey)}</div>
          <div className="risk-category">{a.category}</div>
        </div>
      </div>

      {/* ---- explanation ---- */}
      <div className="card">
        <p style={{ margin: 0, fontSize: 17 }}>{explanation}</p>

        {result.input.transcript && (
          <div className="transcript">
            <b>{t("transcript")}:</b> {result.input.transcript}
          </div>
        )}
        {result.input.ocr_engine && result.input.kind === "screenshot" && (
          <div className="transcript">
            <b>{t("screenshot_text")}:</b> {result.input.original}
          </div>
        )}

        <div className="badges">
          <span className={`badge ${result.engine === "llm" ? "ai" : ""}`}>
            {result.engine === "llm" ? t("engine_ai") : t("engine_rules")}
          </span>
          {result.input.ocr_engine && <span className="badge">OCR: {result.input.ocr_engine}</span>}
          {result.input.stt_engine && <span className="badge">STT: {result.input.stt_engine}</span>}
        </div>
      </div>

      {/* ---- red flags ---- */}
      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>🚩 {t("redflags")}</div>
        <ul className="list">
          {a.indicators.map((ind, i) => (
            <li key={i}>
              <span className="mark bad">{labelKey === "safe" ? "•" : "✗"}</span>
              <span>{ind}</span>
            </li>
          ))}
        </ul>

        {result.urls?.length > 0 && (
          <>
            <div className="section-title">🔗 Links found</div>
            {result.urls.map((u, i) => (
              <div key={i} className={`url-item ${u.verdict}`}>
                <div className="url-verdict">{u.verdict}</div>
                <div>{u.url}</div>
                <div className="muted">{u.reasons.join(" · ")}</div>
              </div>
            ))}
          </>
        )}
      </div>

      {/* ---- RAG playbooks ---- */}
      {result.playbooks?.length > 0 && (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>📚 {t("pattern")}</div>
          {result.playbooks.map((p, i) => (
            <div className="playbook" key={i}>
              <b>{p.title}</b>
              <div>{p.why}</div>
              <div className="meta">
                ✅ {p.do.slice(0, 3).join(" · ")}
                <br />❌ {p.dont.slice(0, 3).join(" · ")}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ---- next steps ---- */}
      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>✅ {t("nextsteps")}</div>
        <ul className="list">
          {a.next_steps.map((s, i) => (
            <li key={i}>
              <span className="mark step">{i + 1}.</span>
              <span>{s}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* ---- actions ---- */}
      <div className="btn-row">
        <button className="btn btn-primary" onClick={playWarning} disabled={speaking}>
          {speaking ? `⏸ ${t("speaking")}` : `🔊 ${t("speak")}`}
        </button>
        {a.guardian_alert || a.risk_label !== "safe" ? (
          <button className="btn btn-red" onClick={sendGuardian}>
            📲 {t("guardian")}
          </button>
        ) : null}
      </div>
      <div className="btn-row">
        <a className="btn btn-outline" href="tel:1930">☎️ {t("call1930")}</a>
        <a className="btn btn-outline" href="https://cybercrime.gov.in" target="_blank" rel="noopener">
          🌐 {t("report")}
        </a>
      </div>

      {audioErr && <p className="muted">🔊 {audioErr}</p>}
      {guardian && (
        <p className="muted">
          {guardian.status === "sent"
            ? `✅ Guardian alert sent to ${guardian.to}`
            : guardian.status === "ready"
              ? `✅ ${t("guardian_note")}`
              : `⚠️ ${guardian.note}`}
        </p>
      )}

      <div style={{ marginTop: 14 }}>
        <button className="btn btn-outline" onClick={onReset}>🔄 {t("recheck")}</button>
      </div>
    </div>
  );
}
