import { useEffect, useState } from "react";
import { collaborationApi } from "../api/collaborationApi";
import type { ProjectAccess } from "../types";
export function useProjectAccess(projectId: string) {
  const [access, setAccess] = useState<ProjectAccess | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { let active = true; setLoading(true); collaborationApi.access(projectId).then((value) => { if (active) setAccess(value); }).catch(() => { if (active) setAccess(null); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [projectId]);
  return { access, loading, can: (capability: string) => Boolean(access?.capabilities?.includes(capability)) };
}
