import { CalendarDays, GitPullRequest, Link2, Mail, RefreshCw, ShieldCheck, Unplug } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { useProjectAccess } from "../../collaboration/hooks/useProjectAccess";
import { workPlanningApi } from "../../work-planning/api/workPlanningApi";
import type { Task } from "../../work-planning/types";
import { integrationsApi } from "../api/integrationsApi";
import type { CalendarEvent, CalendarInfo, CalendarPreview, EmailMessage, ExternalLink, IntegrationAccount, IntegrationsStatus, LinkVisibility, ProjectIntegration, Repository, SourceObject } from "../types";

export function IntegrationsPage() {
  const { t, i18n } = useTranslation();
  const { projectId = "" } = useParams();
  const { can } = useProjectAccess(projectId);
  const canManage = can("integrations.manage");
  const canSync = can("integrations.sync");
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [accounts, setAccounts] = useState<IntegrationAccount[]>([]);
  const [connections, setConnections] = useState<ProjectIntegration[]>([]);
  const [links, setLinks] = useState<ExternalLink[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [calendars, setCalendars] = useState<Record<string, CalendarInfo[]>>({});
  const [repositories, setRepositories] = useState<Record<string, Repository[]>>({});
  const [events, setEvents] = useState<Record<string, CalendarEvent[]>>({});
  const [emails, setEmails] = useState<Record<string, EmailMessage[]>>({});
  const [sourceItems, setSourceItems] = useState<Record<string, SourceObject[]>>({});
  const [emailQuery, setEmailQuery] = useState("");
  const [emailVisibility, setEmailVisibility] = useState<LinkVisibility>("PRIVATE");
  const [selectedTask, setSelectedTask] = useState("");
  const [preview, setPreview] = useState<{ integrationId: string; value: CalendarPreview } | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [nextStatus, nextAccounts, nextConnections, nextLinks, taskList] = await Promise.all([
        integrationsApi.status(),
        integrationsApi.accounts(),
        integrationsApi.projectIntegrations(projectId),
        integrationsApi.externalLinks(projectId),
        workPlanningApi.listTasks(projectId),
      ]);
      setStatus(nextStatus);
      setAccounts(nextAccounts);
      setConnections(nextConnections);
      setLinks(nextLinks);
      setTasks(taskList.items);
      setSelectedTask((current) => current || taskList.items[0]?.id || "");
    } catch {
      setError(t("integrations.errors.load"));
    }
  }, [projectId, t]);

  useEffect(() => { void load(); }, [load]);

  const providerStatus = useMemo(() => new Map(status?.providers.map((item) => [item.provider, item])), [status]);
  const googleAccounts = accounts.filter((item) => item.provider === "GOOGLE");
  const githubAccounts = accounts.filter((item) => item.provider === "GITHUB");

  async function action(key: string, operation: () => Promise<unknown>, reload = true) {
    setBusy(key);
    setError("");
    try {
      await operation();
      if (reload) await load();
    } catch {
      setError(t("integrations.errors.action"));
    } finally {
      setBusy("");
    }
  }

  async function connectProvider(provider: "google" | "github") {
    await action(`oauth-${provider}`, async () => {
      const result = await integrationsApi.startOAuth(provider, `/projects/${projectId}/integrations`);
      window.location.assign(result.authorization_url);
    }, false);
  }

  async function discover(account: IntegrationAccount) {
    if (account.provider === "GOOGLE") {
      await action(`discover-${account.id}`, async () => {
        const result = await integrationsApi.calendars(account.id);
        setCalendars((value) => ({ ...value, [account.id]: result }));
      }, false);
    } else {
      await action(`discover-${account.id}`, async () => {
        const result = await integrationsApi.repositories(account.id);
        setRepositories((value) => ({ ...value, [account.id]: result }));
      }, false);
    }
  }

  async function browseEvents(connection: ProjectIntegration) {
    const start = new Date();
    const end = new Date(start.getTime() + 30 * 24 * 60 * 60 * 1000);
    await action(`events-${connection.id}`, async () => {
      const result = await integrationsApi.calendarEvents(projectId, connection.id, start.toISOString(), end.toISOString());
      setEvents((value) => ({ ...value, [connection.id]: result }));
    }, false);
  }

  async function searchEmail(connection: ProjectIntegration) {
    if (!emailQuery.trim()) return;
    await action(`email-${connection.id}`, async () => {
      const result = await integrationsApi.searchEmail(projectId, connection.id, emailQuery.trim());
      setEmails((value) => ({ ...value, [connection.id]: result }));
    }, false);
  }

  async function browseSource(connection: ProjectIntegration, collection: "issues" | "pull-requests" | "commits") {
    await action(`${collection}-${connection.id}`, async () => {
      const result = await integrationsApi.sourceObjects(projectId, connection.id, collection);
      setSourceItems((value) => ({ ...value, [`${connection.id}:${collection}`]: result }));
    }, false);
  }

  return (
    <div className="workspace-page integrations-workspace">
      <header className="workspace-header">
        <div><p className="eyebrow">{t("integrations.eyebrow")}</p><h1>{t("integrations.title")}</h1><p>{t("integrations.subtitle")}</p></div>
        <Link className="secondary-button" to={`/projects/${projectId}`}>{t("integrations.back")}</Link>
      </header>
      {error && <div className="error-banner" role="alert">{error}</div>}
      {!status?.encryption_configured && <div className="info-banner"><ShieldCheck size={18} />{t("integrations.notConfigured")}</div>}

      <section className="overview-section integration-section">
        <header><div><p className="eyebrow">{t("integrations.accounts.eyebrow")}</p><h2>{t("integrations.accounts.title")}</h2><p>{t("integrations.accounts.help")}</p></div></header>
        <div className="integration-grid">
          {(["GOOGLE", "GITHUB"] as const).map((provider) => {
            const providerAccounts = provider === "GOOGLE" ? googleAccounts : githubAccounts;
            const ProviderIcon = provider === "GOOGLE" ? Mail : GitPullRequest;
            const configured = providerStatus.get(provider)?.configured;
            return <article className="panel-card" key={provider}>
              <div className="integration-card-title"><ProviderIcon size={20} /><h3>{provider === "GOOGLE" ? t("integrations.google") : "GitHub"}</h3></div>
              {!configured && <p>{providerStatus.get(provider)?.reason ?? t("integrations.notConfigured")}</p>}
              {providerAccounts.map((account) => <div className="integration-account" key={account.id}>
                <div><strong>{account.display_name}</strong><span className={`status-pill ${account.status === "CONNECTED" ? "healthy" : "attention"}`}>{t(`integrations.status.${account.status}`)}</span></div>
                <div className="inline-actions">
                  {account.status === "CONNECTED" && <button className="secondary-button" disabled={!canManage || busy !== ""} onClick={() => void discover(account)}>{t("integrations.actions.browse")}</button>}
                  {canManage && <button className="danger-button" disabled={busy !== ""} onClick={() => void action(`disconnect-${account.id}`, () => integrationsApi.disconnectAccount(account.id))}><Unplug size={15} />{t("integrations.actions.disconnect")}</button>}
                </div>
                {provider === "GOOGLE" && calendars[account.id]?.map((calendar) => <button className="link-list-item" key={calendar.id} disabled={!canManage || busy !== ""} onClick={() => void action(`calendar-${calendar.id}`, () => integrationsApi.connectProject(projectId, account.id, "GOOGLE_CALENDAR", calendar.id, calendar.name))}><CalendarDays size={16} />{calendar.name}{calendar.primary ? ` · ${t("integrations.primary")}` : ""}</button>)}
                {provider === "GOOGLE" && canManage && <button className="link-list-item" disabled={busy !== ""} onClick={() => void action(`gmail-${account.id}`, () => integrationsApi.connectProject(projectId, account.id, "GMAIL", "me", "Gmail"))}><Mail size={16} />{t("integrations.gmail.link")}</button>}
                {provider === "GITHUB" && repositories[account.id]?.map((repository) => <button className="link-list-item" key={repository.id} disabled={!canManage || busy !== ""} onClick={() => void action(`repo-${repository.id}`, () => integrationsApi.connectProject(projectId, account.id, "GITHUB_REPOSITORY", repository.full_name, repository.full_name))}><GitPullRequest size={16} />{repository.full_name}{repository.private ? ` · ${t("integrations.private")}` : ""}</button>)}
              </div>)}
              {canManage && configured && <button className="primary-button" disabled={busy !== ""} onClick={() => void connectProvider(provider.toLowerCase() as "google" | "github")}>{providerAccounts.some((item) => item.status === "CONNECTED") ? t("integrations.actions.reconnect") : t("integrations.actions.connect")}</button>}
            </article>;
          })}
        </div>
      </section>

      <section className="overview-section integration-section">
        <header><div><p className="eyebrow">{t("integrations.connections.eyebrow")}</p><h2>{t("integrations.connections.title")}</h2><p>{t("integrations.connections.help")}</p></div></header>
        {connections.length === 0 ? <p className="empty-state">{t("integrations.connections.empty")}</p> : connections.map((connection) => <article className="panel-card integration-connection" key={connection.id}>
          <header><div><strong>{connection.display_name}</strong><span>{t(`integrations.kind.${connection.kind}`)} · {t(`integrations.connectionStatus.${connection.status}`)}</span></div><div className="inline-actions">{canSync && <button className="secondary-button" disabled={busy !== ""} onClick={() => void action(`refresh-${connection.id}`, () => integrationsApi.refreshProject(projectId, connection.id))}><RefreshCw size={15} />{t("integrations.actions.refresh")}</button>}{canManage && <button className="danger-button" disabled={busy !== ""} onClick={() => void action(`remove-${connection.id}`, () => integrationsApi.disconnectProject(projectId, connection.id))}>{t("integrations.actions.unlink")}</button>}</div></header>
          {connection.kind === "GOOGLE_CALENDAR" && <div><button className="secondary-button" disabled={!canSync || busy !== ""} onClick={() => void browseEvents(connection)}>{t("integrations.calendar.browse")}</button><div className="integration-items">{events[connection.id]?.map((event) => <article key={event.id}><div><strong>{event.title}</strong><span>{new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium", timeStyle: "short" }).format(new Date(event.starts_at))}</span><p>{event.location || event.description || t("common.notProvided")}</p></div><div className="inline-actions">{canManage && <button className="secondary-button" onClick={() => void action(`link-event-${event.id}`, () => integrationsApi.linkCalendarEvent(projectId, connection.id, event.id))}><Link2 size={15} />{t("integrations.actions.link")}</button>}{canSync && <button className="primary-button" onClick={() => void action(`preview-${event.id}`, async () => setPreview({ integrationId: connection.id, value: await integrationsApi.previewMeeting(projectId, connection.id, event.id) }), false)}>{t("integrations.calendar.preview")}</button>}</div></article>)}</div></div>}
          {connection.kind === "GMAIL" && <div><div className="integration-search"><input aria-label={t("integrations.gmail.search")} value={emailQuery} onChange={(event) => setEmailQuery(event.target.value)} placeholder={t("integrations.gmail.placeholder")} /><select aria-label={t("integrations.visibility.label")} value={emailVisibility} onChange={(event) => setEmailVisibility(event.target.value as LinkVisibility)}><option value="PRIVATE">{t("integrations.visibility.PRIVATE")}</option><option value="PROJECT">{t("integrations.visibility.PROJECT")}</option><option value="FINANCE">{t("integrations.visibility.FINANCE")}</option></select><button className="primary-button" disabled={!canSync || busy !== ""} onClick={() => void searchEmail(connection)}>{t("integrations.gmail.search")}</button></div><div className="integration-items">{emails[connection.id]?.map((email) => <article key={email.id}><div><strong>{email.subject}</strong><span>{email.sender || t("common.notProvided")}</span><p>{email.snippet}</p></div>{canManage && <button className="secondary-button" onClick={() => void action(`link-email-${email.id}`, () => integrationsApi.linkEmail(projectId, connection.id, email.id, emailVisibility))}>{t("integrations.actions.link")}</button>}</article>)}</div></div>}
          {connection.kind === "GITHUB_REPOSITORY" && <div><div className="inline-actions">{(["issues", "pull-requests", "commits"] as const).map((collection) => <button className="secondary-button" key={collection} disabled={!canSync || busy !== ""} onClick={() => void browseSource(connection, collection)}>{t(`integrations.github.${collection}`)}</button>)}</div><div className="integration-items">{(["issues", "pull-requests", "commits"] as const).flatMap((collection) => sourceItems[`${connection.id}:${collection}`] ?? []).map((item) => <article key={`${item.url}-${item.id}`}><div><strong>{item.title}</strong><span>{item.state}</span><p>{item.summary}</p></div>{canManage && item.number !== null && <div className="integration-task-link"><select aria-label={t("integrations.github.task")} value={selectedTask} onChange={(event) => setSelectedTask(event.target.value)}>{tasks.map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}</select><button className="secondary-button" disabled={!selectedTask} onClick={() => void action(`task-link-${item.id}`, () => integrationsApi.linkTask(projectId, connection.id, item.url.includes("/pull/") ? "GITHUB_PULL_REQUEST" : "GITHUB_ISSUE", item.id, selectedTask, "RELATES_TO"))}>{t("integrations.github.linkTask")}</button></div>}</article>)}</div></div>}
        </article>)}
      </section>

      <section className="overview-section integration-section"><header><div><p className="eyebrow">{t("integrations.links.eyebrow")}</p><h2>{t("integrations.links.title")}</h2><p>{t("integrations.links.help")}</p></div></header>{links.length === 0 ? <p className="empty-state">{t("integrations.links.empty")}</p> : <div className="integration-items">{links.map((item) => <article key={item.id} className={!item.available ? "unavailable" : ""}><div><strong>{item.title}</strong><span>{t(`integrations.object.${item.object_type}`)} · {t(`integrations.visibility.${item.visibility}`)}</span><p>{item.summary}</p></div><div className="inline-actions"><a className="secondary-button" href={item.external_url} target="_blank" rel="noreferrer">{t("integrations.actions.open")}</a>{canSync && <button className="secondary-button" onClick={() => void action(`link-refresh-${item.id}`, () => integrationsApi.refreshLink(projectId, item.id))}>{t("integrations.actions.refresh")}</button>}{canManage && <button className="danger-button" onClick={() => void action(`link-delete-${item.id}`, () => integrationsApi.deleteLink(projectId, item.id))}>{t("integrations.actions.unlink")}</button>}</div></article>)}</div>}</section>

      {preview && <div className="modal-backdrop" role="presentation"><div className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="calendar-preview-title"><h2 id="calendar-preview-title">{t("integrations.calendar.previewTitle")}</h2><h3>{preview.value.event.title}</h3><p>{preview.value.event.description}</p><p>{new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "full", timeStyle: "short" }).format(new Date(preview.value.event.starts_at))}</p><div className="modal-actions"><button className="secondary-button" onClick={() => setPreview(null)}>{t("common.cancel")}</button><button className="primary-button" disabled={!canManage || busy !== ""} onClick={() => void action("import-meeting", async () => { await integrationsApi.importMeeting(projectId, preview.integrationId, preview.value.confirmation_token); setPreview(null); })}>{t("integrations.calendar.confirm")}</button></div></div></div>}
    </div>
  );
}
