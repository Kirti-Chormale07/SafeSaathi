"use client";
import { useEffect, useState } from "react";
import Header from "@/components/Header";
import { fetchDashboard } from "@/lib/api";
import { makeT } from "@/lib/i18n";

function inr(n) {
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)} Cr`;
  if (n >= 100000) return `₹${(n / 100000).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

export default function Dashboard() {
  const [lang, setLang] = useState("en");
  const t = makeT(lang);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = () => fetchDashboard().then(setData).catch((e) => setError(e.message));
    load();
    const id = setInterval(load, 5000); // live updates during the demo
    return () => clearInterval(id);
  }, []);

  const maxCat = data ? Math.max(1, ...Object.values(data.by_category)) : 1;

  return (
    <>
      <Header t={t} lang={lang} setLang={setLang} />
      <main className="shell">
        <h2 style={{ margin: "18px 0 6px" }}>📊 Impact Dashboard</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Live stats from this session. Privacy note: nothing is stored on a server - the log
          clears when the backend restarts.
        </p>

        {error && <div className="alert-error">⚠️ {error}</div>}

        {!data ? (
          <div className="card">Loading...</div>
        ) : (
          <>
            <div className="stat-grid">
              <div className="stat">
                <div className="num">{data.total}</div>
                <div className="cap">Messages checked</div>
              </div>
              <div className="stat">
                <div className="num red">{data.by_label.scam}</div>
                <div className="cap">Scams caught</div>
              </div>
              <div className="stat">
                <div className="num amber">{data.by_label.suspicious}</div>
                <div className="cap">Suspicious flagged</div>
              </div>
              <div className="stat">
                <div className="num">{inr(data.money_saved)}</div>
                <div className="cap">Money saved (est.)</div>
              </div>
            </div>

            <div className="card" style={{ marginTop: 14 }}>
              <div className="section-title" style={{ marginTop: 0 }}>
                🎯 Scam types detected
              </div>
              {Object.keys(data.by_category).length === 0 && (
                <p className="muted">No scams detected yet - run a sample from the Check tab.</p>
              )}
              {Object.entries(data.by_category).map(([cat, count]) => (
                <div className="bar-row" key={cat}>
                  <div className="bar-label">{cat}</div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(count / maxCat) * 100}%` }} />
                  </div>
                  <div className="bar-val">{count}</div>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>🕘 Recent checks</div>
              {data.recent.length === 0 && <p className="muted">Nothing yet.</p>}
              <ul className="list">
                {data.recent.map((e, i) => (
                  <li key={i}>
                    <span
                      className="mark"
                      style={{
                        color:
                          e.label === "scam" ? "#dc2626" : e.label === "suspicious" ? "#d97706" : "#16a34a",
                      }}
                    >
                      ●
                    </span>
                    <span>
                      <b>{e.category}</b> - {e.score}/100
                      <span className="muted"> · {e.kind} · {new Date(e.ts + "Z").toLocaleTimeString()}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </main>
    </>
  );
}
