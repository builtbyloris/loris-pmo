import { AlertTriangle, BellRing, Gauge, History, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { intelligenceApi } from "../api/intelligenceApi";
import type { AlertSeverity, AlertStatus, KPIValue, ProjectIntelligence } from "../types";

interface Props {
  projectId: string;
  value: ProjectIntelligence;
  onChange: (next: ProjectIntelligence) => void;
  readOnly: boolean;
}

const KEY_KPIS = [
  "task_completion_rate",
  "overdue_tasks",
  "budget_utilization",
  "critical_risks",
  "critical_issues",
  "overloaded_members",
];

export function ProjectIntelligencePanel({ projectId, value, onChange, readOnly }: Props) {
  const { t, i18n } = useTranslation();
  const [statusFilter, setStatusFilter] = useState<AlertStatus | "ALL">("ALL");
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity | "ALL">("ALL");
  const [savingId, setSavingId] = useState("");
  const kpis = useMemo(
    () => KEY_KPIS.map((key) => value.kpis.find((item) => item.key === key)).filter(Boolean) as KPIValue[],
    [value.kpis],
  );
  const alerts = value.alerts.filter(
    (item) =>
      (statusFilter === "ALL" || item.status === statusFilter) &&
      (severityFilter === "ALL" || item.severity === severityFilter),
  );
  const attention = value.alerts.filter((item) => item.status !== "RESOLVED");
  const formatKpi = (item: KPIValue) => {
    if (!item.available) return t("intelligence.unavailable");
    if (item.unit === "percent") return `${item.value}%`;
    if (item.unit === "currency")
      return new Intl.NumberFormat(i18n.resolvedLanguage, { style: "currency", currency: "EUR" }).format(Number(item.value));
    return String(item.value ?? "—");
  };
  async function acknowledge(alertId: string) {
    setSavingId(alertId);
    try {
      const updated = await intelligenceApi.acknowledge(projectId, alertId);
      onChange({ ...value, alerts: value.alerts.map((item) => (item.id === alertId ? updated : item)) });
    } finally {
      setSavingId("");
    }
  }
  return <>
    <section className="overview-section intelligence-health">
      <header><div><p className="eyebrow">{t("intelligence.eyebrow")}</p><h2>{t("intelligence.health.title")}</h2><p>{t("intelligence.health.description")}</p></div><div className={`health-score health-${value.health.status?.toLowerCase() ?? "unavailable"}`}><Gauge /><strong>{value.health.score ?? "—"}</strong><span>{value.health.status ? t(`intelligence.health.status.${value.health.status}`) : t("intelligence.unavailable")}</span></div></header>
      <div className="health-dimensions">{value.health.dimensions.map((item) => <article key={item.key} className={!item.available ? "unavailable" : ""}><div><span>{t(`intelligence.health.dimensions.${item.key}`)}</span><strong>{item.score ?? "—"}</strong></div><div className="health-track"><span style={{ width: `${item.score ?? 0}%` }} /></div><small>{item.available ? t("intelligence.health.weight", { weight: item.effective_weight }) : t(`intelligence.reasons.${item.reason}`)}</small></article>)}</div>
      {value.health.drivers.length > 0 && <div className="health-drivers"><h3>{t("intelligence.health.drivers")}</h3>{value.health.drivers.map((driver) => <span className={`severity-${driver.severity.toLowerCase()}`} key={driver.key}>{t(`intelligence.drivers.${driver.key}`, driver.evidence)}</span>)}</div>}
      {value.health.history.length > 1 && <details className="health-history"><summary><History size={16} />{t("intelligence.health.history")}</summary>{value.health.history.slice(0, 5).map((item) => <div key={item.id}><span>{new Intl.DateTimeFormat(i18n.resolvedLanguage).format(new Date(item.created_at))}</span><strong>{item.score} · {t(`intelligence.health.status.${item.status}`)}</strong></div>)}</details>}
    </section>
    <section className="overview-section"><header><div><p className="eyebrow">{t("intelligence.kpis.eyebrow")}</p><h2>{t("intelligence.kpis.title")}</h2></div></header><div className="planning-overview-grid intelligence-kpis">{kpis.map((item) => <article className={item.status === "critical" ? "attention" : ""} key={item.key}><ShieldCheck /><span>{t(`intelligence.kpis.labels.${item.key}`)}</span><strong>{formatKpi(item)}</strong>{!item.available && <small>{t(`intelligence.reasons.${item.reason}`)}</small>}</article>)}</div></section>
    <section className="overview-section attention-required"><header><div><p className="eyebrow">{t("intelligence.attention.eyebrow")}</p><h2>{t("intelligence.attention.title")}</h2></div><BellRing /></header>{attention.length === 0 ? <div className="section-empty"><ShieldCheck /><p>{t("intelligence.attention.empty")}</p></div> : <div className="attention-list">{attention.slice(0, 5).map((alert) => <article className={`alert-${alert.severity.toLowerCase()}`} key={alert.id}><span>{t(`intelligence.alertSeverity.${alert.severity}`)}</span><div><strong>{t(alert.title_key)}</strong><p>{t(alert.reason_key, alert.evidence)}</p></div></article>)}</div>}</section>
    <section className="overview-section alerts-section"><header><div><p className="eyebrow">{t("intelligence.alerts.eyebrow")}</p><h2>{t("intelligence.alerts.title")}</h2><p>{t("intelligence.alerts.description", { count: value.automation_rules.filter((rule) => rule.enabled).length })}</p></div><AlertTriangle /></header><div className="alert-filters"><label>{t("intelligence.alerts.statusFilter")}<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as AlertStatus | "ALL")}><option value="ALL">{t("common.all")}</option>{(["ACTIVE", "ACKNOWLEDGED", "RESOLVED"] as AlertStatus[]).map((status) => <option key={status} value={status}>{t(`intelligence.alertStatus.${status}`)}</option>)}</select></label><label>{t("intelligence.alerts.severityFilter")}<select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value as AlertSeverity | "ALL")}><option value="ALL">{t("common.all")}</option>{(["INFO", "WARNING", "CRITICAL"] as AlertSeverity[]).map((severity) => <option key={severity} value={severity}>{t(`intelligence.alertSeverity.${severity}`)}</option>)}</select></label></div>{alerts.length === 0 ? <div className="section-empty"><BellRing /><p>{t("intelligence.alerts.empty")}</p></div> : <div className="alerts-list">{alerts.map((alert) => <article key={alert.id} className={`alert-${alert.severity.toLowerCase()} ${alert.status === "RESOLVED" ? "resolved" : ""}`}><div><span>{t(`intelligence.alertSeverity.${alert.severity}`)}</span><span>{t(`intelligence.alertStatus.${alert.status}`)}</span></div><h3>{t(alert.title_key)}</h3><p>{t(alert.reason_key, alert.evidence)}</p>{alert.status === "ACTIVE" && !readOnly && <button className="secondary-button" disabled={savingId === alert.id} onClick={() => void acknowledge(alert.id)}>{t("intelligence.alerts.acknowledge")}</button>}</article>)}</div>}</section>
  </>;
}
