import { ArrowLeft, Download, FileText, GitCompare, RefreshCw, Search, Sparkles, Trash2, Upload } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../../services/api";
import { useProjectAccess } from "../../collaboration/hooks/useProjectAccess";
import { documentsApi } from "../api/documentsApi";
import type { DocumentCategory, KnowledgeAnswer, KnowledgeComparison, KnowledgeQueryResponse, KnowledgeStatus, ProjectDocument } from "../types";

const categories: DocumentCategory[] = ["REQUIREMENTS", "SPECIFICATIONS", "MEETING_NOTES", "CONTRACTS", "REPORTS", "FINANCE", "OTHER"];

export function DocumentsPage() {
  const { t, i18n } = useTranslation();
  const { projectId = "" } = useParams();
  const { can } = useProjectAccess(projectId);
  const canManage = can("documents.manage");
  const canFinance = can("finance.read");
  const canUseAi = can("ai.assistant");
  const [items, setItems] = useState<ProjectDocument[]>([]);
  const [knowledgeStatus, setKnowledgeStatus] = useState<KnowledgeStatus | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState<DocumentCategory>("OTHER");
  const [description, setDescription] = useState("");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<KnowledgeQueryResponse | null>(null);
  const [answer, setAnswer] = useState<KnowledgeAnswer | null>(null);
  const [comparison, setComparison] = useState<KnowledgeComparison | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [documents, status] = await Promise.all([
        documentsApi.list(projectId),
        documentsApi.knowledgeStatus(projectId),
      ]);
      setItems(documents);
      setKnowledgeStatus(status);
      setSelected((current) => current.filter((id) => documents.some((item) => item.id === id)));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : t("documents.error"));
    }
  }, [projectId, t]);

  useEffect(() => { void load(); }, [load]);

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true); setError("");
    try {
      await documentsApi.upload(projectId, file, category, description);
      setFile(null); setDescription(""); await load();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : t("documents.error"));
    } finally { setBusy(false); }
  }

  async function search(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setBusy(true); setError(""); setAnswer(null); setComparison(null);
    try { setResult(await documentsApi.query(projectId, query)); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : t("documents.error")); }
    finally { setBusy(false); }
  }

  async function askDocuments() {
    if (!query.trim()) return;
    setBusy(true); setError(""); setComparison(null);
    try { setAnswer(await documentsApi.answer(projectId, query, selected, language(i18n.resolvedLanguage))); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : t("documents.error")); }
    finally { setBusy(false); }
  }

  async function compareDocuments() {
    if (selected.length < 2) return;
    setBusy(true); setError(""); setAnswer(null);
    try { setComparison(await documentsApi.compare(projectId, selected, query || t("documents.compareDefault"), language(i18n.resolvedLanguage))); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : t("documents.error")); }
    finally { setBusy(false); }
  }

  async function reindex(documentId: string) {
    setBusy(true); setError("");
    try { await documentsApi.reindex(projectId, documentId); await load(); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : t("documents.error")); }
    finally { setBusy(false); }
  }

  function toggle(documentId: string) {
    setSelected((current) => current.includes(documentId)
      ? current.filter((id) => id !== documentId)
      : current.length < 4 ? [...current, documentId] : current);
  }

  return <div className="page-stack">
    <Link className="back-link" to={`/projects/${projectId}`}><ArrowLeft size={16}/>{t("documents.back")}</Link>
    <header className="page-header"><div><p className="eyebrow">{t("documents.eyebrow")}</p><h1>{t("documents.title")}</h1><p>{t("documents.subtitle")}</p></div><Link className="secondary-button" to={`/projects/${projectId}/reports`}>{t("documents.openReports")}</Link></header>
    {error && <div className="inline-error">{error}</div>}

    {canManage && <section className="overview-section"><header><div><h2>{t("documents.upload")}</h2><p>{t("documents.uploadHelp")}</p></div></header><form className="s12-form" onSubmit={upload}><input aria-label={t("documents.file")} type="file" accept=".pdf,.docx,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.webp" onChange={(event) => setFile(event.target.files?.[0] ?? null)}/><select value={category} onChange={(event) => setCategory(event.target.value as DocumentCategory)}>{categories.filter((value) => canFinance || value !== "FINANCE").map((value) => <option key={value} value={value}>{t(`documents.categories.${value}`)}</option>)}</select><input value={description} onChange={(event) => setDescription(event.target.value)} placeholder={t("documents.description")}/><button className="primary-button" disabled={!file || busy}><Upload size={16}/>{t("documents.upload")}</button></form></section>}

    <section className="overview-section"><header><div><h2>{t("documents.library")}</h2><p>{t("documents.libraryHelp")}</p></div></header>
      {knowledgeStatus && <div className="knowledge-status" aria-label={t("documents.indexStatus")}><strong>{t("documents.indexStatus")}</strong><span>{t("documents.indexSummary", { indexed: knowledgeStatus.indexed_chunks, total: knowledgeStatus.total_chunks })}</span><small>{knowledgeStatus.provider_available ? `${knowledgeStatus.embedding_model} · ${knowledgeStatus.embedding_version}` : t("documents.lexicalFallback")}</small></div>}
      {items.length === 0 ? <div className="section-empty"><FileText/><p>{t("documents.empty")}</p></div> : <div className="s12-list">{items.map((item) => <article key={item.id}><input type="checkbox" checked={selected.includes(item.id)} disabled={item.status !== "READY"} onChange={() => toggle(item.id)} aria-label={t("documents.selectForComparison", { name: item.original_filename })}/><FileText/><div><strong>{item.original_filename}</strong><small>{t(`documents.categories.${item.category}`)} · {(item.size_bytes / 1024).toFixed(1)} KB · {item.status}</small><span className={`semantic-badge semantic-${item.semantic_status.toLowerCase()}`}>{t(`documents.semanticStatus.${item.semantic_status}`)}</span>{item.semantic_indexed_at && <small>{t("documents.lastIndexed", { date: new Date(item.semantic_indexed_at).toLocaleString() })}</small>}{item.description && <p>{item.description}</p>}{(item.processing_error || item.semantic_error) && <p className="inline-error">{item.processing_error || t("documents.semanticDegraded")}</p>}</div><button className="icon-button" onClick={() => documentsApi.download(projectId, item.id)} aria-label={t("documents.download")}><Download size={16}/></button>{canManage && item.status === "READY" && <button className="icon-button" disabled={busy} onClick={() => void reindex(item.id)} aria-label={t("documents.reindex")}><RefreshCw size={16}/></button>}{canManage && <button className="icon-button danger" onClick={() => window.confirm(t("documents.deleteConfirm")) && void documentsApi.remove(projectId, item.id).then(load)} aria-label={t("common.delete")}><Trash2 size={16}/></button>}</article>)}</div>}
    </section>

    <section className="overview-section"><header><div><h2>{t("documents.knowledge")}</h2><p>{t("documents.knowledgeHelp")}</p></div>{canUseAi && <Link className="secondary-button" to={`/projects/${projectId}/assistant`}>{t("documents.askAi")}</Link>}</header><form className="s12-search" onSubmit={search}><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("documents.searchPlaceholder")}/><button className="secondary-button" disabled={busy}><Search size={16}/>{t("documents.search")}</button>{canUseAi && <button type="button" className="secondary-button" disabled={busy || !query.trim()} onClick={() => void askDocuments()}><Sparkles size={16}/>{t("documents.askDocuments")}</button>}{canUseAi && <button type="button" className="secondary-button" disabled={busy || selected.length < 2} onClick={() => void compareDocuments()}><GitCompare size={16}/>{t("documents.compare")}</button>}</form>
      {result && <p className="retrieval-indicator">{t(`documents.retrievalMode.${result.diagnostics.mode}`)} · {t("documents.selectedChunks", { count: result.diagnostics.selected_chunks })}</p>}
      {result?.matches.map((match) => <article className="s12-match" key={match.evidence_id}><strong>{match.filename}</strong><small>{locationLabel(match.location)} · {t(`documents.retrievalMode.${match.retrieval_mode}`)}</small><p>{match.excerpt}</p></article>)}
      {answer && <article className="knowledge-answer"><h3>{t("documents.groundedAnswer")}</h3><p>{answer.answer}</p><EvidenceList evidence={answer.evidence}/></article>}
      {comparison && <article className="knowledge-answer"><h3>{t("documents.comparison")}</h3><p>{comparison.summary}</p><ComparisonList title={t("documents.agreements")} items={comparison.agreements}/><ComparisonList title={t("documents.differences")} items={comparison.differences}/><ComparisonList title={t("documents.conflicts")} items={comparison.potential_conflicts}/><ComparisonList title={t("documents.missingInformation")} items={comparison.missing_information}/><EvidenceList evidence={comparison.evidence}/></article>}
    </section>
  </div>;
}

function language(value: string | undefined): "en" | "it" { return value?.startsWith("it") ? "it" : "en"; }
function locationLabel(location: Record<string, unknown> | null): string { if (!location) return ""; return Object.entries(location).map(([key, value]) => `${key}: ${String(value)}`).join(" · "); }
function ComparisonList({ title, items }: { title: string; items: string[] }) { if (!items.length) return null; return <div><strong>{title}</strong><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>; }
function EvidenceList({ evidence }: { evidence: { ref: string; label: string; detail: string }[] }) { const { t } = useTranslation(); return <div className="knowledge-evidence"><strong>{t("documents.evidence")}</strong>{evidence.map((item) => <small key={item.ref}>{item.label} · {item.detail}</small>)}</div>; }
