import { CalendarRange, Gauge, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../../services/api";
import { controlApi } from "../../control/api/controlApi";
import { peopleApi } from "../../people/api/peopleApi";
import { workPlanningApi } from "../../work-planning/api/workPlanningApi";
import { assistantApi } from "../api/assistantApi";
import type { AIBriefing, AIScenario, AIScenarioType } from "../types";

type View = "briefing" | "weekly" | "scenarios";
interface Props { projectId: string; view: View; providerAvailable: boolean; readOnly: boolean; }

export function OperationalAIWorkspace({ projectId, view, providerAvailable, readOnly }: Props) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage?.startsWith("it") ? "it" : "en";
  const [daily, setDaily] = useState<AIBriefing | null>(null);
  const [weekly, setWeekly] = useState<AIBriefing[]>([]);
  const [scenarios, setScenarios] = useState<AIScenario[]>([]);
  const [options, setOptions] = useState<{ tasks: { id: string; title: string }[]; milestones: { id: string; title: string }[]; members: { id: string; person: { name: string } }[]; risks: { id: string; title: string }[] }>({ tasks: [], milestones: [], members: [], risks: [] });
  const [scenarioType, setScenarioType] = useState<AIScenarioType>("TASK_DELAY");
  const [entityId, setEntityId] = useState("");
  const [amount, setAmount] = useState("7");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [nextDaily, nextWeekly, nextScenarios, tasks, milestones, members, risks] = await Promise.all([
        assistantApi.daily(projectId), assistantApi.weekly(projectId), assistantApi.scenarios(projectId),
        workPlanningApi.listTasks(projectId), workPlanningApi.listMilestones(projectId), peopleApi.listMembers(projectId), controlApi.listRisks(projectId),
      ]);
      setDaily(nextDaily); setWeekly(nextWeekly); setScenarios(nextScenarios);
      setOptions({ tasks: tasks.items, milestones, members, risks: risks.items });
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : t("operationalAI.errors.load")); }
    finally { setLoading(false); }
  }, [projectId, t]);
  useEffect(() => { void load(); }, [load]);

  async function generate(kind: "daily" | "weekly", force = false) {
    setWorking(true); setError("");
    try {
      if (kind === "daily") setDaily(await assistantApi.generateDaily(projectId, language, force));
      else {
        const result = await assistantApi.generateWeekly(projectId, language, force);
        setWeekly((current) => [result, ...current]);
      }
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : t("operationalAI.errors.generate")); }
    finally { setWorking(false); }
  }

  const choices = scenarioType === "TASK_DELAY" ? options.tasks : scenarioType === "MILESTONE_DELAY" ? options.milestones : scenarioType === "RESOURCE_UNAVAILABLE" ? options.members.map((item) => ({ id: item.id, title: item.person.name })) : scenarioType === "RISK_OCCURS" ? options.risks : [];
  async function runScenario() {
    setWorking(true); setError("");
    const input: Parameters<typeof assistantApi.runScenario>[1] = { type: scenarioType, language };
    if (scenarioType === "TASK_DELAY") { input.task_id = entityId; input.delay_days = Number(amount); }
    if (scenarioType === "MILESTONE_DELAY") { input.milestone_id = entityId; input.delay_days = Number(amount); }
    if (scenarioType === "RESOURCE_UNAVAILABLE") input.member_id = entityId;
    if (scenarioType === "RISK_OCCURS") input.risk_id = entityId;
    if (scenarioType === "COST_INCREASE") input.cost_increase = amount;
    try { const result = await assistantApi.runScenario(projectId, input); setScenarios((current) => [result, ...current]); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : t("operationalAI.errors.generate")); }
    finally { setWorking(false); }
  }

  if (loading) return <div className="content-state"><span className="spinner" />{t("common.loading")}</div>;
  const disabled = working || readOnly || !providerAvailable;
  return <section className="workspace-panel operational-ai">
    {error && <div className="error-banner" role="alert">{error}</div>}
    {view === "briefing" && <>
      <WorkspaceHeader icon={<Sparkles />} title={t("operationalAI.daily.title")} body={t("operationalAI.daily.body")}>
        <button className="primary-button" disabled={disabled} onClick={() => void generate("daily", Boolean(daily))}><RefreshCw size={15} />{daily ? t("operationalAI.refresh") : t("operationalAI.generate")}</button>
      </WorkspaceHeader>
      {!daily ? <Empty text={t("operationalAI.daily.empty")} /> : <BriefingCard value={daily} />}
    </>}
    {view === "weekly" && <>
      <WorkspaceHeader icon={<CalendarRange />} title={t("operationalAI.weekly.title")} body={t("operationalAI.weekly.body")}>
        <button className="primary-button" disabled={disabled} onClick={() => void generate("weekly")}><Sparkles size={15} />{t("operationalAI.generate")}</button>
      </WorkspaceHeader>
      {weekly.length === 0 ? <Empty text={t("operationalAI.weekly.empty")} /> : weekly.map((item) => <BriefingCard key={item.id} value={item} />)}
    </>}
    {view === "scenarios" && <>
      <WorkspaceHeader icon={<Gauge />} title={t("operationalAI.scenario.title")} body={t("operationalAI.scenario.body")} />
      <div className="scenario-builder">
        <label>{t("operationalAI.scenario.type")}<select value={scenarioType} onChange={(e) => { setScenarioType(e.target.value as AIScenarioType); setEntityId(""); }}>{["TASK_DELAY", "MILESTONE_DELAY", "RESOURCE_UNAVAILABLE", "COST_INCREASE", "RISK_OCCURS"].map((type) => <option key={type} value={type}>{t(`operationalAI.scenario.types.${type}`)}</option>)}</select></label>
        {choices.length > 0 && <label>{t("operationalAI.scenario.subject")}<select value={entityId} onChange={(e) => setEntityId(e.target.value)}><option value="">—</option>{choices.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}
        {(scenarioType === "TASK_DELAY" || scenarioType === "MILESTONE_DELAY" || scenarioType === "COST_INCREASE") && <label>{scenarioType === "COST_INCREASE" ? t("operationalAI.scenario.cost") : t("operationalAI.scenario.days")}<input type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} /></label>}
        <button className="primary-button" disabled={disabled || (scenarioType !== "COST_INCREASE" && !entityId)} onClick={() => void runScenario()}>{t("operationalAI.scenario.run")}</button>
      </div>
      <p className="assistant-disclaimer">{t("operationalAI.scenario.disclaimer")}</p>
      {scenarios.map((item) => <article className="operational-card" key={item.id}><header><strong>{t(`operationalAI.scenario.types.${item.type}`)}</strong><time>{new Date(item.created_at).toLocaleString(i18n.resolvedLanguage)}</time></header><p>{item.interpretation.interpretation}</p><List title={t("operationalAI.scenario.impacts")} values={item.interpretation.impacts} /><List title={t("operationalAI.scenario.options")} values={item.interpretation.options} /><Evidence values={item.evidence} /></article>)}
    </>}
  </section>;
}

function WorkspaceHeader({ icon, title, body, children }: { icon: React.ReactNode; title: string; body: string; children?: React.ReactNode }) { return <header className="operational-header"><div>{icon}<span><h2>{title}</h2><p>{body}</p></span></div>{children}</header>; }
function Empty({ text }: { text: string }) { return <div className="assistant-empty compact"><Sparkles /><p>{text}</p></div>; }
function BriefingCard({ value }: { value: AIBriefing }) {
  const { t, i18n } = useTranslation(); const content = value.content as Record<string, unknown>;
  const summary = String(content.summary ?? content.executive_summary ?? "");
  const attention = (content.attention_items ?? []) as { priority: string; title: string; reason: string }[];
  const groups = ["progress", "setbacks", "decisions", "risks_and_issues", "next_week_focus"];
  return <article className="operational-card"><header><strong>{value.kind === "DAILY" ? t("operationalAI.daily.title") : t("operationalAI.weekly.title")}</strong><time>{new Date(value.generated_at).toLocaleString(i18n.resolvedLanguage)}</time></header><p>{summary}</p>{attention.map((item) => <div className={`attention-row ${item.priority}`} key={item.title}><strong>{item.title}</strong><span>{item.reason}</span></div>)}{groups.map((key) => <List key={key} title={t(`operationalAI.weekly.sections.${key}`)} values={(content[key] ?? []) as string[]} />)}{typeof content.financial_summary === "string" && <p><strong>{t("operationalAI.weekly.sections.financial_summary")}:</strong> {content.financial_summary}</p>}<Evidence values={value.evidence} /></article>;
}
function List({ title, values }: { title: string; values: string[] }) { return values.length ? <section><h3>{title}</h3><ul>{values.map((item) => <li key={item}>{item}</li>)}</ul></section> : null; }
function Evidence({ values }: { values: { ref: string; label: string; detail: string }[] }) { const { t } = useTranslation(); return values.length ? <details><summary>{t("assistant.evidence")}</summary><ul>{values.map((item) => <li key={item.ref}><strong>{item.label}</strong> · {item.detail}</li>)}</ul></details> : null; }
