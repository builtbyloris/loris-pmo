import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { FinanceWorkspacePage } from "./features/finance/pages/FinanceWorkspacePage";
import { PeopleWorkspacePage } from "./features/people/pages/PeopleWorkspacePage";
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
          <Route path="projects/:projectId/people" element={<PeopleWorkspacePage />} />
          <Route path="projects/:projectId/finance" element={<FinanceWorkspacePage />} />
          <Route path="copilot" element={<PlaceholderPage area="copilot" />} />
          <Route path="settings" element={<PlaceholderPage area="settings" />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
