/* SafeSaathi API client - all calls go through the Next.js /api proxy. */

async function handle(res) {
  if (res.ok) return res.json();
  let detail = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
    else if (Array.isArray(body?.detail)) detail = body.detail.map((d) => d.msg).join("; ");
  } catch {
    /* keep default message */
  }
  const err = new Error(detail);
  err.status = res.status;
  throw err;
}

export async function analyzeText(text, lang) {
  return handle(await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang }),
  }));
}

export async function analyzeScreenshot(file, lang) {
  const fd = new FormData();
  fd.append("file", file);
  return handle(await fetch(`/api/analyze/screenshot?lang=${lang}`, { method: "POST", body: fd }));
}

export async function analyzeVoice(blob, lang) {
  const fd = new FormData();
  fd.append("file", blob, "snippet.webm");
  return handle(await fetch(`/api/analyze/voice?lang=${lang}`, { method: "POST", body: fd }));
}

export async function fetchSamples() {
  return handle(await fetch("/api/samples"));
}

export async function speak(text, lang) {
  return handle(await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang }),
  }));
}

export async function alertGuardian(message, riskLabel) {
  return handle(await fetch("/api/guardian", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, risk_label: riskLabel }),
  }));
}

export async function fetchDashboard() {
  return handle(await fetch("/api/dashboard"));
}
