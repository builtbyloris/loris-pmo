import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { collaborationApi } from "../api/collaborationApi";
import type { CommentEntityType, ProjectComment } from "../types";
export function CommentsPanel({ projectId, entityType, entityId, canWrite = true }: { projectId: string; entityType: CommentEntityType; entityId: string; canWrite?: boolean }) {
  const { t } = useTranslation(); const [items, setItems] = useState<ProjectComment[]>([]); const [body, setBody] = useState(""); const [saving, setSaving] = useState(false);
  const load = useCallback(() => collaborationApi.comments(projectId, entityType, entityId).then(setItems), [projectId, entityType, entityId]);
  useEffect(() => { void load(); }, [load]);
  async function submit(event: FormEvent) { event.preventDefault(); if (!body.trim()) return; setSaving(true); try { await collaborationApi.addComment(projectId, entityType, entityId, body); setBody(""); await load(); } finally { setSaving(false); } }
  async function edit(item: ProjectComment) { const next = window.prompt(t("collaboration.comments.edit"), item.body); if (next === null || !next.trim() || next.trim() === item.body) return; await collaborationApi.updateComment(projectId, item.id, next); await load(); }
  return <section className="comments-panel"><h3>{t("collaboration.comments.title")}</h3>{items.length === 0 && <p>{t("collaboration.comments.empty")}</p>}<ul>{items.map((item) => <li key={item.id}><strong>{item.author_display_name ?? item.author_email}</strong><time>{new Date(item.created_at).toLocaleString()}</time><p>{item.body}</p>{canWrite && item.can_edit && <div><button type="button" className="text-button" onClick={() => void edit(item)}>{t("common.edit")}</button><button type="button" className="text-button" onClick={() => void collaborationApi.removeComment(projectId, item.id).then(load)}>{t("common.delete")}</button></div>}</li>)}</ul>{canWrite && <form onSubmit={submit}><textarea aria-label={t("collaboration.comments.add")} value={body} onChange={(event) => setBody(event.target.value)} maxLength={4000} /><button className="primary-button" disabled={saving}>{t("collaboration.comments.add")}</button></form>}</section>;
}
