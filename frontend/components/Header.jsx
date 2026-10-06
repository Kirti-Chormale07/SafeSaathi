"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LANGS } from "@/lib/i18n";

export default function Header({ t, lang, setLang }) {
  const pathname = usePathname();
  return (
    <>
      <header className="header">
        <div className="header-inner">
          <div className="logo" aria-hidden>🛡️</div>
          <div>
            <h1>SafeSaathi</h1>
            <div className="tagline">{t("tagline")}</div>
          </div>
          <div className="spacer" />
          <div className="lang-select" role="group" aria-label="Language">
            {LANGS.map((l) => (
              <button
                key={l.code}
                className={lang === l.code ? "active" : ""}
                onClick={() => setLang?.(l.code)}
                type="button"
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <nav className="bottom-nav">
        <Link href="/" className={pathname === "/" ? "active" : ""}>
          <span className="icon">🔍</span>
          {t("home")}
        </Link>
        <Link href="/dashboard" className={pathname === "/dashboard" ? "active" : ""}>
          <span className="icon">📊</span>
          {t("dashboard")}
        </Link>
      </nav>
    </>
  );
}
