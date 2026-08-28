import { useCallback, useEffect, useState } from "react";

import { projectsApi } from "../api/projectsApi";
import type { ProjectFilters, ProjectListResponse } from "../types";

export function useProjects(filters: ProjectFilters) {
  const [data, setData] = useState<ProjectListResponse | null>(null);
  const [error, setError] = useState(false);
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    setError(false);
    const timer = window.setTimeout(() => {
      projectsApi
        .list(filters)
        .then((result) => active && setData(result))
        .catch(() => active && setError(true));
    }, filters.search ? 220 : 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [filters.search, filters.status, filters.priority, filters.include_archived, filters.sort_by, filters.sort_order, revision]);

  return { data, error, reload };
}
