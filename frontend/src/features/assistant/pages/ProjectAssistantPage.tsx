import {
  AlertCircle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  ExternalLink,
  Send,
  Sparkles,
  UserRound,
  Lightbulb,
  ListChecks,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../../services/api";
import { projectsApi } from "../../projects/api/projectsApi";
import type { Project } from "../../projects/types";
import { assistantApi } from "../api/assistantApi";
import { AIAnalysisWorkspace } from "../components/AIAnalysisWorkspace";
import type { AIHistoryMessage, AIStatus, ConversationEntry } from "../types";

const STARTER_KEYS = [
  "attention",
  "changed",
  "health",
  "tasks",
  "budget",
  "risks",
  "workload",
  "decisions",
] as const;

export function ProjectAssistantPage() {
  const { t, i18n } = useTranslation();
  const { projectId: routeProjectId } = useParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(routeProjectId ?? "");
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [view, setView] = useState<"assistant" | "insights" | "recommendations">("assistant");
  const [entries, setEntries] = useState<ConversationEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const conversationEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    projectsApi
      .list({ include_archived: true, sort_by: "updated_at", sort_order: "desc" })
      .then((result) => {
        if (!active) return;
        setProjects(result.items);
        setProjectId((current) => current || result.items[0]?.id || "");
      })
      .catch(() => active && setError(t("assistant.errors.projects")))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [t]);

  useEffect(() => {
    if (!projectId) {
      setStatus(null);
      return;
    }
    let active = true;
    setStatus(null);
    setError("");
    assistantApi
      .status(projectId)
      .then((next) => active && setStatus(next))
      .catch(() => active && setError(t("assistant.errors.status")));
    return () => {
      active = false;
    };
  }, [projectId, t]);

  useEffect(() => {
    const marker = conversationEnd.current;
    if (typeof marker?.scrollIntoView === "function") {
      marker.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [entries, sending]);

  const selectedProject = projects.find((project) => project.id === projectId);
  const starterQuestions = useMemo(
    () => STARTER_KEYS.map((key) => t(`assistant.starters.${key}`)),
    [t],
  );

  function history(): AIHistoryMessage[] {
    return entries.slice(-6).map((entry) => ({ role: entry.role, content: entry.content }));
  }

  async function ask(message: string) {
    const question = message.trim();
    if (!question || !projectId || sending || status?.available !== true) return;
    const priorHistory = history();
    setEntries((current) => [...current, { role: "user", content: question }]);
    setInput("");
    setSending(true);
    setError("");
    try {
      const response = await assistantApi.chat(
        projectId,
        question,
        priorHistory,
        i18n.resolvedLanguage?.startsWith("it") ? "it" : "en",
      );
      setEntries((current) => [
        ...current,
        { role: "assistant", content: response.answer, response },
      ]);
    } catch (reason) {
      const code = reason instanceof ApiError ? reason.code : "ai_unavailable";
      if (code === "ai_not_configured") {
        setStatus((current) =>
          current ? { ...current, available: false, reason: "not_configured" } : current,
        );
      }
      setError(t(`assistant.errors.${code}`, { defaultValue: t("assistant.errors.unavailable") }));
    } finally {
      setSending(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(input);
  }

  if (loading) {
    return (
      <div className="content-state">
        <span className="spinner" />
        {t("common.loading")}
      </div>
    );
  }

  return (
    <div className="assistant-page page-stack">
      {routeProjectId && (
        <Link className="back-link" to={`/projects/${routeProjectId}`}>
          <ArrowLeft size={16} />
          {t("assistant.backToProject")}
        </Link>
      )}
      <header className="assistant-hero">
        <div>
          <p className="eyebrow">{t("assistant.eyebrow")}</p>
          <h1>{t("assistant.title")}</h1>
          <p>{t("assistant.subtitle")}</p>
        </div>
        <div className="assistant-boundary">
          <CheckCircle2 size={17} />
          <span>{t("assistant.readOnly")}</span>
        </div>
      </header>

      {projects.length === 0 ? (
        <section className="assistant-empty">
          <Sparkles size={28} />
          <h2>{t("assistant.noProjects.title")}</h2>
          <p>{t("assistant.noProjects.body")}</p>
          <Link className="primary-button" to="/projects">
            {t("assistant.noProjects.action")}
          </Link>
        </section>
      ) : (
        <>
          <section className="assistant-context-bar">
            <label>
              <span>{t("assistant.projectContext")}</span>
              <select
                value={projectId}
                onChange={(event) => {
                  setProjectId(event.target.value);
                  setEntries([]);
                }}
                disabled={Boolean(routeProjectId)}
              >
                {projects.map((project) => (
                  <option value={project.id} key={project.id}>
                    {project.code} · {project.name}
                  </option>
                ))}
              </select>
            </label>
            {selectedProject && (
              <Link to={`/projects/${selectedProject.id}`} className="text-button">
                {t("assistant.openProject")}
                <ExternalLink size={14} />
              </Link>
            )}
            {status && (
              <span className={`assistant-provider ${status.available ? "available" : "unavailable"}`}>
                {status.available ? t("assistant.available") : t("assistant.unavailable")}
                <small>{status.provider} · {status.model}</small>
              </span>
            )}
          </section>

          <nav className="assistant-view-tabs" aria-label={t("aiAnalysis.views.label")}>
            <button type="button" className={view === "assistant" ? "active" : ""} onClick={() => setView("assistant")}><Bot size={15} />{t("aiAnalysis.views.assistant")}</button>
            <button type="button" className={view === "insights" ? "active" : ""} onClick={() => setView("insights")}><Lightbulb size={15} />{t("aiAnalysis.views.insights")}</button>
            <button type="button" className={view === "recommendations" ? "active" : ""} onClick={() => setView("recommendations")}><ListChecks size={15} />{t("aiAnalysis.views.recommendations")}</button>
          </nav>

          {view === "assistant" ? (
            status?.available === false ? (
            <section className="assistant-unavailable" role="status">
              <AlertCircle size={24} />
              <div>
                <h2>{t("assistant.unavailableTitle")}</h2>
                <p>{t("assistant.unavailableBody")}</p>
              </div>
            </section>
          ) : (
            <div className="assistant-layout">
              <aside className="assistant-starters">
                <p className="eyebrow">{t("assistant.startersEyebrow")}</p>
                <h2>{t("assistant.startersTitle")}</h2>
                <div>
                  {starterQuestions.map((question) => (
                    <button type="button" key={question} onClick={() => void ask(question)}>
                      {question}
                    </button>
                  ))}
                </div>
              </aside>

              <section className="assistant-conversation" aria-label={t("assistant.conversation")}>
                <div className="assistant-messages" aria-live="polite">
                  {entries.length === 0 && (
                    <div className="assistant-welcome">
                      <Bot size={27} />
                      <h2>{t("assistant.welcomeTitle")}</h2>
                      <p>{t("assistant.welcomeBody")}</p>
                    </div>
                  )}
                  {entries.map((entry, index) => (
                    <article className={`assistant-message ${entry.role}`} key={`${entry.role}-${index}`}>
                      <div className="assistant-avatar">
                        {entry.role === "assistant" ? <Bot size={17} /> : <UserRound size={17} />}
                      </div>
                      <div>
                        <strong>
                          {entry.role === "assistant" ? t("assistant.assistant") : t("assistant.you")}
                        </strong>
                        <p>{entry.content}</p>
                        {entry.response && <ResponseDetails value={entry.response} />}
                      </div>
                    </article>
                  ))}
                  {sending && (
                    <article className="assistant-message assistant loading-message">
                      <div className="assistant-avatar"><Bot size={17} /></div>
                      <div><span className="spinner" />{t("assistant.thinking")}</div>
                    </article>
                  )}
                  <div ref={conversationEnd} />
                </div>
                {error && <div className="inline-error" role="alert">{error}</div>}
                <form className="assistant-composer" onSubmit={submit}>
                  <label className="sr-only" htmlFor="assistant-message">
                    {t("assistant.inputLabel")}
                  </label>
                  <textarea
                    id="assistant-message"
                    rows={2}
                    maxLength={4000}
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        submit(event);
                      }
                    }}
                    placeholder={t("assistant.placeholder")}
                    disabled={sending || status?.available !== true}
                  />
                  <button className="primary-button" disabled={!input.trim() || sending}>
                    <Send size={16} />
                    {t("assistant.send")}
                  </button>
                </form>
                <small className="assistant-disclaimer">{t("assistant.disclaimer")}</small>
              </section>
            </div>
            )
          ) : (
            <AIAnalysisWorkspace
              key={`${projectId}-${view}`}
              projectId={projectId}
              view={view}
              providerAvailable={status?.available === true}
              readOnly={Boolean(selectedProject?.archived_at)}
            />
          )}
        </>
      )}
    </div>
  );
}

function ResponseDetails({ value }: { value: NonNullable<ConversationEntry["response"]> }) {
  const { t } = useTranslation();
  return (
    <div className="assistant-response-details">
      {value.evidence.length > 0 && (
        <section>
          <h3>{t("assistant.evidence")}</h3>
          <ul>{value.evidence.map((item) => <li key={item.ref}><strong>{item.label}</strong><span>{item.detail}</span></li>)}</ul>
        </section>
      )}
      {value.assumptions.length > 0 && <section><h3>{t("assistant.assumptions")}</h3><ul>{value.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></section>}
      {value.missing_information.length > 0 && <section><h3>{t("assistant.missing")}</h3><ul>{value.missing_information.map((item) => <li key={item}>{item}</li>)}</ul></section>}
      {value.suggested_followups.length > 0 && <section><h3>{t("assistant.followups")}</h3><div className="assistant-followups">{value.suggested_followups.map((item) => <span key={item}>{item}</span>)}</div></section>}
    </div>
  );
}
