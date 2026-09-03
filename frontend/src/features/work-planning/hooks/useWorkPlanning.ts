import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { peopleApi } from "../../people/api/peopleApi";
import { workPlanningApi } from "../api/workPlanningApi";
import type { MilestoneInput, ScheduleChange, SchedulePreview, Task, TaskInput, TaskStatus, WorkPlanningData } from "../types";

export function useWorkPlanning(projectId: string) {
  const { t } = useTranslation();
  const [data, setData] = useState<WorkPlanningData | null>(null);
  const [error, setError] = useState("");
  const [mutationError, setMutationError] = useState("");
  const [movingTaskId, setMovingTaskId] = useState("");
  const [schedulePreview, setSchedulePreview] = useState<SchedulePreview | null>(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const [taskList, milestones, dependencies, summary, members, schedule] = await Promise.all([
        workPlanningApi.listTasks(projectId),
        workPlanningApi.listMilestones(projectId),
        workPlanningApi.listDependencies(projectId),
        workPlanningApi.summary(projectId),
        peopleApi.listMembers(projectId),
        workPlanningApi.schedule(projectId),
      ]);
      setData({ tasks: taskList.items, milestones, dependencies, summary, members, schedule });
    } catch {
      setError(t("workPlanning.loadError"));
    }
  }, [projectId, t]);

  useEffect(() => void load(), [load]);

  const mutate = useCallback(async (operation: () => Promise<unknown>) => {
    setMutationError("");
    try {
      await operation();
      await load();
      return true;
    } catch {
      setMutationError(t("workPlanning.actions.error"));
      return false;
    }
  }, [load, t]);

  const moveTask = useCallback(async (taskId: string, status: TaskStatus) => {
    if (!data) return false;
    const previous = data.tasks;
    const optimistic = previous.map((task): Task => task.id === taskId ? { ...task, status, completion_percentage: status === "DONE" ? 100 : task.completion_percentage } : task);
    setData({ ...data, tasks: optimistic });
    setMutationError("");
    setMovingTaskId(taskId);
    try {
      await workPlanningApi.updateTask(projectId, taskId, { status });
      await load();
      return true;
    } catch {
      setData({ ...data, tasks: previous });
      setMutationError(t("workPlanning.actions.error"));
      return false;
    } finally {
      setMovingTaskId("");
    }
  }, [data, load, projectId, t]);

  return {
    data,
    error,
    mutationError,
    movingTaskId,
    clearMutationError: () => setMutationError(""),
    reload: load,
    createTask: (input: TaskInput) => mutate(() => workPlanningApi.createTask(projectId, input)),
    updateTaskStatus: moveTask,
    updateTaskAssignees: (taskId: string, assigneeIds: string[]) => mutate(() => workPlanningApi.updateTask(projectId, taskId, { assignee_ids: assigneeIds })),
    archiveTask: (taskId: string) => mutate(() => workPlanningApi.archiveTask(projectId, taskId)),
    createMilestone: (input: MilestoneInput) => mutate(() => workPlanningApi.createMilestone(projectId, input)),
    updateMilestone: (milestoneId: string, input: Partial<MilestoneInput>) => mutate(() => workPlanningApi.updateMilestone(projectId, milestoneId, input)),
    createDependency: (sourceId: string, targetId: string, type: "BLOCKS" | "DEPENDS_ON" | "RELATED_TO") => mutate(() => workPlanningApi.createDependency(projectId, sourceId, targetId, type)),
    deleteDependency: (dependencyId: string) => mutate(() => workPlanningApi.deleteDependency(projectId, dependencyId)),
    schedulePreview,
    previewSchedule: async (change: ScheduleChange) => {
      setMutationError("");
      try { const value = await workPlanningApi.previewSchedule(projectId, change); setSchedulePreview(value); return true; }
      catch { setMutationError(t("workPlanning.schedule.previewError")); return false; }
    },
    cancelSchedulePreview: () => setSchedulePreview(null),
    applySchedule: async () => {
      if (!schedulePreview) return false;
      const ok = await mutate(() => workPlanningApi.applySchedule(projectId, schedulePreview));
      if (ok) setSchedulePreview(null);
      return ok;
    },
    createBaseline: (replace = false) => mutate(() => workPlanningApi.createBaseline(projectId, replace)),
  };
}
