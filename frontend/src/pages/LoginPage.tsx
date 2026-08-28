import { ArrowRight, LockKeyhole } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { FullPageLoader } from "../components/FullPageLoader";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeToggle } from "../components/ThemeToggle";
import { useAuth } from "../features/auth/AuthContext";

export function LoginPage() {
  const { t } = useTranslation();
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme ||= "dark";
  }, []);

  useEffect(() => {
    if (status === "authenticated" && !submitting) {
      const destination = (location.state as { from?: string } | null)?.from ?? "/portfolio";
      navigate(destination, { replace: true });
    }
  }, [location.state, navigate, status, submitting]);

  if (status === "authenticated") return <FullPageLoader />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(false);
    try {
      await login(email, password);
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-tools"><LanguageSwitcher /><ThemeToggle /></div>
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-brand">
          <div className="brand-mark large" aria-hidden="true">L</div>
          <div><strong>{t("brand.name")}</strong><span>{t("brand.tagline")}</span></div>
        </div>
        <p className="eyebrow">{t("login.eyebrow")}</p>
        <h1 id="login-heading">{t("login.title")}</h1>
        <p className="page-subtitle">{t("login.subtitle")}</p>
        <form onSubmit={handleSubmit} className="login-form">
          <label>
            <span>{t("login.email")}</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            <span>{t("login.password")}</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && <div className="inline-error" role="alert">{t("login.error")}</div>}
          <button className="primary-button" disabled={submitting} type="submit">
            <span>{submitting ? t("login.submitting") : t("login.submit")}</span>
            <ArrowRight size={18} aria-hidden="true" />
          </button>
        </form>
        <p className="login-note"><LockKeyhole size={15} />{t("login.note")}</p>
      </section>
      <div className="login-atmosphere" aria-hidden="true">
        <div className="orbit orbit-one" /><div className="orbit orbit-two" />
        <div className="signal-card signal-one"><span>01</span><i /></div>
        <div className="signal-card signal-two"><span>PMO</span><i /></div>
      </div>
    </main>
  );
}
