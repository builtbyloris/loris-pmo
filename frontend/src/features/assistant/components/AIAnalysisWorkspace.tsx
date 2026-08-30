import {
  AlertTriangle,
  Check,
  Clock3,
  EyeOff,
  Lightbulb,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../../services/api";
import { assistantApi } from "../api/assistantApi";
import type {
  AIAnalysisSummary,
  AIInsight,
  AIRecommendation,
  AIRecommendationStatus,
} from "../types";

interface Props {
  projectId: string;
  view: "insights" | "recommendations";
  providerAvailable: boolean;
  readOnly: boolean;
}

const RECOMMENDATION_STATUSES: AIRecommendationStatus[] = [
  "PENDING",
  "ACCEPTED",
  "REJECTED",
  "IGNORED",
];

export function AIAnalysisWorkspace({
  projectId,
  view,
  providerAvailable,
  readOnly,
}: Props) {
  const { t, i18n } = useTranslation();
  const [summary, setSummary] = useState<AIAnalysisSummary | null>(null);
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [recommendationStatus, setRecommendationStatus] =
    useState<AIRecommendationStatus>("PENDING");
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [acting, setActing] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextInsights, nextRecommendations] = await Promise.all([
        assistantApi.analysisSummary(projectId),
        assistantApi.insights(projectId),
        assistantApi.recommendations(projectId),
      ]);
      setSummary(nextSummary);
      setInsights(nextInsights);
      setRecommendations(nextRecommendations);
    } catch {
      setError(t("aiAnalysis.errors.load"));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function analyze(force = false) {
    setAnalyzing(true);
    setError("");
    setMessage("");
    try {
      const result = await assistantApi.analyze(
        projectId,
        i18n.resolvedLanguage?.startsWith("it") ? "it" : "en",
        force,
      );
      setSummary(result.summary);
      setInsights(result.insights);
      setRecommendations(result.recommendations);
      setMessage(
        result.unchanged
          ? t("aiAnalysis.unchanged")
          : result.generated
            ? t("aiAnalysis.generated")
            : t("aiAnalysis.noSignals"),
      );
    } catch (reason) {
      const code = reason instanceof ApiError ? reason.code : "ai_unavailable";
      setError(
        t(`aiAnalysis.errors.${code}`, {
          defaultValue: t("aiAnalysis.errors.analyze"),
        }),
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function dismiss(insightId: string) {
    setActing(insightId);
    setError("");
    try {
      const next = await assistantApi.dismissInsight(projectId, insightId);
      setInsights((current) =>
        current.map((item) => (item.id === insightId ? next : item)),
      );
      if (summary) {
        setSummary({
          ...summary,
          active_insights: Math.max(0, summary.active_insights - 1),
          critical_insights:
            next.severity === "CRITICAL"
              ? Math.max(0, summary.critical_insights - 1)
              : summary.critical_insights,
        });
      }
    } catch {
      setError(t("aiAnalysis.errors.action"));
    } finally {
      setActing("");
    }
  }

  async function decide(
    item: AIRecommendation,
    action: "accept" | "reject" | "ignore",
  ) {
    setActing(item.id);
    setError("");
    try {
      const next = await assistantApi.decideRecommendation(
        projectId,
        item.id,
        action,
        reasons[item.id],
      );
      setRecommendations((current) =>
        current.map((value) => (value.id === item.id ? next : value)),
      );
      if (summary) {
        setSummary({
          ...summary,
          pending_recommendations: Math.max(0, summary.pending_recommendations - 1),
        });
      }
    } catch {
      setError(t("aiAnalysis.errors.action"));
    } finally {
      setActing("");
    }
  }

  if (loading) {
    return (
      <div className="content-state">
        <span className="spinner" />
        {t("common.loading")}
      </div>
    );
  }

  const filteredRecommendations = recommendations.filter(
    (item) => item.status === recommendationStatus,
  );

  return (
    <section className="ai-analysis-workspace">
      <header className="ai-analysis-toolbar">
        <div>
          <p className="eyebrow">{t("aiAnalysis.eyebrow")}</p>
          <h2>
            {view === "insights"
              ? t("aiAnalysis.insights.title")
              : t("aiAnalysis.recommendations.title")}
          </h2>
          <p>{t("aiAnalysis.description")}</p>
        </div>
        <div className="ai-analysis-actions">
          {summary?.last_analyzed_at && (
            <span>
              <Clock3 size={14} />
              {t("aiAnalysis.lastAnalyzed", {
                value: new Intl.DateTimeFormat(i18n.resolvedLanguage, {
                  dateStyle: "medium",
                  timeStyle: "short",
                }).format(new Date(summary.last_analyzed_at)),
              })}
            </span>
          )}
          <button
            className="primary-button"
            type="button"
            onClick={() => void analyze(false)}
            disabled={!providerAvailable || readOnly || analyzing}
          >
            {analyzing ? <span className="spinner" /> : <Sparkles size={16} />}
            {analyzing ? t("aiAnalysis.analyzing") : t("aiAnalysis.analyze")}
          </button>
          {summary?.last_analyzed_at && (
            <button
              className="icon-button"
              type="button"
              title={t("aiAnalysis.force")}
              aria-label={t("aiAnalysis.force")}
              onClick={() => void analyze(true)}
              disabled={!providerAvailable || readOnly || analyzing}
            >
              <RefreshCw size={15} />
            </button>
          )}
        </div>
      </header>

      {!providerAvailable && (
        <div className="assistant-unavailable compact" role="status">
          <AlertTriangle size={20} />
          <p>{t("aiAnalysis.providerUnavailable")}</p>
        </div>
      )}
      {message && <div className="success-banner">{message}</div>}
      {error && <div className="inline-error" role="alert">{error}</div>}

      {view === "insights" ? (
        <InsightList
          items={insights}
          acting={acting}
          readOnly={readOnly}
          onDismiss={dismiss}
        />
      ) : (
        <>
          <nav className="ai-status-tabs" aria-label={t("aiAnalysis.recommendations.filters")}>
            {RECOMMENDATION_STATUSES.map((status) => (
              <button
                type="button"
                className={recommendationStatus === status ? "active" : ""}
                onClick={() => setRecommendationStatus(status)}
                key={status}
              >
                {t(`aiAnalysis.status.${status}`)}
                <span>{recommendations.filter((item) => item.status === status).length}</span>
              </button>
            ))}
          </nav>
          <RecommendationList
            items={filteredRecommendations}
            acting={acting}
            readOnly={readOnly}
            reasons={reasons}
            setReasons={setReasons}
            onDecide={decide}
          />
        </>
      )}
    </section>
  );
}

function Evidence({ items }: { items: AIInsight["evidence"] }) {
  const { t } = useTranslation();
  return (
    <details className="ai-evidence">
      <summary>{t("aiAnalysis.evidence")} · {items.length}</summary>
      <ul>
        {items.map((item) => (
          <li key={item.ref}><strong>{item.label}</strong><span>{item.detail}</span></li>
        ))}
      </ul>
    </details>
  );
}

function Confidence({ value }: { value: number }) {
  const { t } = useTranslation();
  return (
    <span className="ai-confidence" title={t("aiAnalysis.confidenceHelp")}>
      {t("aiAnalysis.confidence")} {Math.round(value * 100)}%
    </span>
  );
}

function InsightList({ items, acting, readOnly, onDismiss }: {
  items: AIInsight[];
  acting: string;
  readOnly: boolean;
  onDismiss: (id: string) => Promise<void>;
}) {
  const { t } = useTranslation();
  if (items.length === 0) {
    return <div className="assistant-empty compact"><Lightbulb /><h3>{t("aiAnalysis.insights.empty")}</h3><p>{t("aiAnalysis.insights.emptyBody")}</p></div>;
  }
  return <div className="ai-card-list">{items.map((item) => (
    <article className={`ai-card severity-${item.severity.toLowerCase()}`} key={item.id}>
      <header><div><span>{t(`aiAnalysis.severity.${item.severity}`)}</span><span>{t(`aiAnalysis.insightStatus.${item.status}`)}</span></div><Confidence value={item.confidence} /></header>
      <h3>{item.title}</h3><p>{item.summary}</p><p className="ai-explanation">{item.explanation}</p>
      <Evidence items={item.evidence} />
      {item.status === "ACTIVE" && !readOnly && <footer><button className="text-button" type="button" disabled={acting === item.id} onClick={() => void onDismiss(item.id)}><EyeOff size={14} />{t("aiAnalysis.dismiss")}</button></footer>}
    </article>
  ))}</div>;
}

function RecommendationList({ items, acting, readOnly, reasons, setReasons, onDecide }: {
  items: AIRecommendation[];
  acting: string;
  readOnly: boolean;
  reasons: Record<string, string>;
  setReasons: (value: Record<string, string>) => void;
  onDecide: (item: AIRecommendation, action: "accept" | "reject" | "ignore") => Promise<void>;
}) {
  const { t } = useTranslation();
  if (items.length === 0) return <div className="assistant-empty compact"><Sparkles /><h3>{t("aiAnalysis.recommendations.empty")}</h3><p>{t("aiAnalysis.recommendations.emptyBody")}</p></div>;
  return <div className="ai-card-list recommendation-list">{items.map((item) => (
    <article className="ai-card" key={item.id}>
      <header><span>{t(`aiAnalysis.status.${item.status}`)}</span><Confidence value={item.confidence} /></header>
      <h3>{item.title}</h3>
      <dl><div><dt>{t("aiAnalysis.recommendation")}</dt><dd>{item.recommendation}</dd></div><div><dt>{t("aiAnalysis.why")}</dt><dd>{item.reasoning_summary}</dd></div>{item.expected_impact && <div><dt>{t("aiAnalysis.expectedImpact")}</dt><dd>{item.expected_impact}</dd></div>}</dl>
      {item.alternatives.length > 0 && <section className="ai-alternatives"><h4>{t("aiAnalysis.alternatives")}</h4><ul>{item.alternatives.map((value) => <li key={value}>{value}</li>)}</ul></section>}
      <Evidence items={item.evidence} />
      {item.decision_reason && <p className="ai-decision-reason"><strong>{t("aiAnalysis.decisionReason")}</strong>{item.decision_reason}</p>}
      {item.status === "PENDING" && !readOnly && <footer className="recommendation-actions"><label><span>{t("aiAnalysis.reasonOptional")}</span><textarea rows={2} value={reasons[item.id] ?? ""} onChange={(event) => setReasons({ ...reasons, [item.id]: event.target.value })} /></label><div><button className="primary-button" type="button" disabled={acting === item.id} onClick={() => void onDecide(item, "accept")}><Check size={14} />{t("aiAnalysis.accept")}</button><button className="secondary-button" type="button" disabled={acting === item.id} onClick={() => void onDecide(item, "reject")}><X size={14} />{t("aiAnalysis.reject")}</button><button className="text-button" type="button" disabled={acting === item.id} onClick={() => void onDecide(item, "ignore")}><EyeOff size={14} />{t("aiAnalysis.ignore")}</button></div></footer>}
    </article>
  ))}</div>;
}
