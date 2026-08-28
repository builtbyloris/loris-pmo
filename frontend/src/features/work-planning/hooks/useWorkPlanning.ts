import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { workPlanningApi } from "../api/workPlanningApi";
import type { MilestoneInput, Task, TaskInput, TaskStatus, WorkPlanningData } from "../types";

export function useWorkPlanning(projectId: string) {
  const { t } = useTranslation();
  const [data, setData] = useState<WorkPlanningData | null>(null);
  const [error, setError] = useState("");
  const [mutationError, setMutationError] = useState("");
  const [movingTaskId, setMovingTaskId] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [taskList, milestones, dependencies, summary] = await Promise.all([
        workPlanningApi.listTasks(projectId),
        workPlanningApi.listMilestones(projectId),
        workPlanningApi.listDependencies(projectId),
        workPlanningApi.summary(projectId),
      ]);
      setData({ tasks: taskList.items, milestones, dependencies, summary });
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
    archiveTask: (taskId: string) => mutate(() => workPlanningApi.archiveTask(projectId, taskId)),
    createMilestone: (input: MilestoneInput) => mutate(() => workPlanningApi.createMilestone(projectId, input)),
    updateMilestone: (milestoneId: string, input: Partial<MilestoneInput>) => mutate(() => workPlanningApi.updateMilestone(projectId, milestoneId, input)),
    createDependency: (sourceId: string, targetId: string, type: "BLOCKS" | "DEPENDS_ON" | "RELATED_TO") => mutate(() => workPlanningApi.createDependency(projectId, sourceId, targetId, type)),
    deleteDependency: (dependencyId: string) => mutate(() => workPlanningApi.deleteDependency(projectId, dependencyId)),
  };
}
