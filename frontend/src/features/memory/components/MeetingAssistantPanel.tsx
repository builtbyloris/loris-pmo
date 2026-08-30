import { Check, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../../services/api";
import { assistantApi } from "../../assistant/api/assistantApi";
import type { MeetingAIAnalysis } from "../../assistant/types";

export function MeetingAssistantPanel({ projectId, meetingId, readOnly, onConfirmed }: { projectId: string; meetingId: string; readOnly: boolean; onConfirmed: () => void }) {
  const { t, i18n } = useTranslation();
  const [analysis, setAnalysis] = useState<MeetingAIAnalysis | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(() => assistantApi.meetingAnalysis(projectId, meetingId).then(setAnalysis).catch(() => undefined), [projectId, meetingId]);
  useEffect(() => { void load(); }, [load]);
  async function analyze() {
    setWorking(true); setError("");
    try { setAnalysis(await assistantApi.analyzeMeeting(projectId, meetingId, i18n.resolvedLanguage?.startsWith("it") ? "it" : "en", Boolean(analysis))); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : t("meetingAI.error")); }
    finally { setWorking(false); }
  }
  async function review(id: string, action: "confirm" | "reject") {
    setWorking(true); setError("");
    try { await assistantApi.reviewMeetingProposal(projectId, meetingId, id, action); await load(); if (action === "confirm") onConfirmed(); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : t("meetingAI.error")); }
    finally { setWorking(false); }
  }
  return <section className="meeting-ai-panel">
    <header><div><Sparkles size={16} /><strong>{t("meetingAI.title")}</strong></div><button className="text-button compact" disabled={working || readOnly} onClick={() => void analyze()}>{analysis ? t("meetingAI.refresh") : t("meetingAI.analyze")}</button></header>
    <small>{t("meetingAI.boundary")}</small>{error && <p className="field-error">{error}</p>}
    {analysis && <><p>{analysis.summary}</p><div className="meeting-proposals">{analysis.proposals.map((proposal) => <article key={proposal.id}><span className="control-badge">{t(`meetingAI.kind.${proposal.kind}`)}</span><strong>{proposal.payload.title}</strong><p>{proposal.payload.description}</p><span className="control-badge">{t(`meetingAI.status.${proposal.status}`)}</span>{proposal.status === "PENDING" && !readOnly && <div><button className="text-button compact" disabled={working} onClick={() => void review(proposal.id, "confirm")}><Check size={14} />{t("meetingAI.confirm")}</button><button className="text-button compact danger-text" disabled={working} onClick={() => void review(proposal.id, "reject")}><X size={14} />{t("meetingAI.reject")}</button></div>}</article>)}</div></>}
  </section>;
}
