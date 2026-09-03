import { Navigate, Route, Routes } from "react-router-dom";

import { ProjectAssistantPage } from "./features/assistant/pages/ProjectAssistantPage";
import { CollaboratorsPage } from "./features/collaboration/pages/CollaboratorsPage";
import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { ControlWorkspacePage } from "./features/control/pages/ControlWorkspacePage";
import { DocumentsPage } from "./features/documents/pages/DocumentsPage";
import { ReportsPage } from "./features/documents/pages/ReportsPage";
import { FinanceWorkspacePage } from "./features/finance/pages/FinanceWorkspacePage";
import { IntegrationsPage } from "./features/integrations/pages/IntegrationsPage";
import { PeopleWorkspacePage } from "./features/people/pages/PeopleWorkspacePage";
import { ProjectMemoryPage } from "./features/memory/pages/ProjectMemoryPage";
import { PortfolioPage } from "./features/projects/pages/PortfolioPage";
import { ProjectOverviewPage } from "./features/projects/pages/ProjectOverviewPage";
import { ProjectsPage } from "./features/projects/pages/ProjectsPage";
import { WorkPlanningPage } from "./features/work-planning/pages/WorkPlanningPage";
import { AppShell } from "./layouts/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/portfolio" replace />} />
          <Route path="portfolio" element={<PortfolioPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:projectId" element={<ProjectOverviewPage />} />
          <Route path="projects/:projectId/work" element={<WorkPlanningPage />} />
          <Route path="projects/:projectId/collaborators" element={<CollaboratorsPage />} />
          <Route path="projects/:projectId/people" element={<PeopleWorkspacePage />} />
          <Route path="projects/:projectId/finance" element={<FinanceWorkspacePage />} />
          <Route path="projects/:projectId/integrations" element={<IntegrationsPage />} />
          <Route path="projects/:projectId/control" element={<ControlWorkspacePage />} />
          <Route path="projects/:projectId/memory" element={<ProjectMemoryPage />} />
          <Route path="projects/:projectId/documents" element={<DocumentsPage />} />
          <Route path="projects/:projectId/reports" element={<ReportsPage />} />
          <Route path="projects/:projectId/assistant" element={<ProjectAssistantPage />} />
          <Route path="copilot" element={<ProjectAssistantPage />} />
          <Route path="settings" element={<PlaceholderPage area="settings" />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
