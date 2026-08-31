import { apiRequest } from "../../../services/api";
import type { DocumentCategory, ImportPreview, KnowledgeMatch, ProjectDocument, ProjectReport, ReportType } from "../types";

const base = (projectId: string) => `/api/v1/projects/${projectId}`;
export const documentsApi = {
  list: (projectId: string) => apiRequest<ProjectDocument[]>(`${base(projectId)}/documents`),
  upload(projectId: string, file: File, category: DocumentCategory, description: string) {
    const body = new FormData(); body.append("file", file); body.append("category", category); if (description) body.append("description", description);
    return apiRequest<ProjectDocument>(`${base(projectId)}/documents`, { method: "POST", body });
  },
  update: (projectId: string, documentId: string, data: Partial<Pick<ProjectDocument, "category" | "description">>) => apiRequest<ProjectDocument>(`${base(projectId)}/documents/${documentId}`, { method: "PATCH", body: JSON.stringify(data) }),
  remove: (projectId: string, documentId: string) => apiRequest<void>(`${base(projectId)}/documents/${documentId}`, { method: "DELETE" }),
  download: (projectId: string, documentId: string) => { window.location.assign(`${base(projectId)}/documents/${documentId}/download`); },
  query: (projectId: string, query: string) => apiRequest<{ matches: KnowledgeMatch[] }>(`${base(projectId)}/knowledge/query`, { method: "POST", body: JSON.stringify({ query }) }),
  report: (projectId: string, type: ReportType) => apiRequest<ProjectReport>(`${base(projectId)}/reports/${type}`),
  reportPdf: (projectId: string, type: ReportType) => { window.location.assign(`${base(projectId)}/reports/${type}/pdf`); },
  export: (projectId: string, dataset: string, format: "csv" | "xlsx") => { window.location.assign(`${base(projectId)}/exports/${dataset}/${format}`); },
  importPreview(projectId: string, target: "TASKS" | "EXPENSES", file: File) { const body = new FormData(); body.append("file", file); return apiRequest<ImportPreview>(`${base(projectId)}/imports/${target}/preview`, { method: "POST", body }); },
  importConfirm: (projectId: string, batchId: string) => apiRequest<{ imported_count: number }>(`${base(projectId)}/imports/${batchId}/confirm`, { method: "POST" }),
};
