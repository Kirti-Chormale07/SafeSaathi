"use client";
import { useEffect, useRef, useState } from "react";

function fmt(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}

/** Big red record button -> MediaRecorder blob (audio/webm). */
export default function VoiceRecorder({ t, onComplete, disabled }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [supported, setSupported] = useState(true);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    if (typeof window !== "undefined" && !navigator.mediaDevices?.getUserMedia) {
      setSupported(false);
    }
    return () => {
      clearInterval(timerRef.current);
      mediaRef.current?.stream?.getTracks().forEach((tr) => tr.stop());
    };
  }, []);

  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((tr) => tr.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
        clearInterval(timerRef.current);
        setRecording(false);
        if (blob.size > 0) onComplete(blob);
      };
      rec.start();
      mediaRef.current = rec;
      setSeconds(0);
      setRecording(true);
      timerRef.current = setInterval(() => {
        setSeconds((s) => {
          if (s + 1 >= 60) {
            mediaRef.current?.stop();
            return 60;
          }
          return s + 1;
        });
      }, 1000);
    } catch {
      setSupported(false);
    }
  }

  function stop() {
    mediaRef.current?.state && mediaRef.current.stop();
  }

  if (!supported) {
    return (
      <div className="card">
        <p className="muted">
          🎤 Microphone recording is not available in this browser. Type what was said in the
          first tab, or try a sample instead.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="record-wrap">
        <button
          type="button"
          className={`record-btn ${recording ? "recording" : ""}`}
          onClick={recording ? stop : start}
          disabled={disabled}
          aria-label={recording ? "Stop recording" : "Start recording"}
        >
          {recording ? "⏹" : "🎙️"}
        </button>
        <div className="record-time">{fmt(seconds)}</div>
        <div className="record-hint">
          {recording ? "Recording... tap to stop (max 60s)" : t("voice_hint")}
        </div>
      </div>
    </div>
  );
}
