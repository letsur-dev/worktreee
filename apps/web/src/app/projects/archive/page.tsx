"use client";

import { Project, Task } from "@/types";
import Link from "next/link";
import { useEffect, useState, useCallback } from "react";

function StatusBadge({ status }: { status: string }) {
  const normalizedStatus = status === "pending" ? "in_progress" : status;
  const styles: Record<string, string> = {
    in_progress: "bg-warning-600 text-white",
    in_review: "bg-blue-600 text-white",
    completed: "bg-success-600 text-white",
  };
  const labels: Record<string, string> = {
    in_progress: "in progress",
    in_review: "in review",
    completed: "completed",
  };
  return (
    <span
      className={`${styles[normalizedStatus] || styles.in_progress} px-2 py-0.5 rounded text-xs font-medium`}
    >
      {labels[normalizedStatus] || normalizedStatus}
    </span>
  );
}

interface ArchivedTaskWithProject extends Task {
  projectName: string;
  projectTitle?: string;
  repoPath: string;
}

interface ArchivedProject {
  name: string;
  title?: string;
  repo_path: string;
  machine: string;
  task_count: number;
  deleted_at: string;
}

interface TaskActionsProps {
  project: string;
  task: Task;
  onUpdated: () => void;
}

function TaskActions({ project, task, onUpdated }: TaskActionsProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleRestore = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/restore-task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, task_name: task.name }),
      });
      if (res.ok) onUpdated();
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`'${task.name}' 태스크를 완전히 삭제하시겠습니까?\n워크트리도 함께 삭제됩니다.`)) return;
    setIsLoading(true);
    try {
      const res = await fetch("/api/delete-task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, task_name: task.name }),
      });
      if (res.ok) onUpdated();
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return <span className="text-xs text-gray-500">...</span>;
  }

  return (
    <div className="flex gap-1 ml-auto">
      <button
        onClick={handleRestore}
        className="px-2 py-0.5 text-xs text-blue-400 hover:bg-blue-600/20 rounded transition"
      >
        복구
      </button>
      <button
        onClick={handleDelete}
        className="px-2 py-0.5 text-xs text-red-400 hover:bg-red-600/20 rounded transition"
      >
        삭제
      </button>
    </div>
  );
}

function ProjectActions({ project, onUpdated }: { project: ArchivedProject; onUpdated: () => void }) {
  const [isLoading, setIsLoading] = useState(false);

  const handleRestore = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/restore-project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project: project.name }),
      });
      if (res.ok) onUpdated();
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return <span className="text-xs text-gray-500">...</span>;
  }

  return (
    <button
      onClick={handleRestore}
      className="px-2 py-0.5 text-xs text-blue-400 hover:bg-blue-600/20 rounded transition"
    >
      복구
    </button>
  );
}

export default function ArchivePage() {
  const [archivedTasks, setArchivedTasks] = useState<ArchivedTaskWithProject[]>([]);
  const [archivedProjects, setArchivedProjects] = useState<ArchivedProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [groupBy, setGroupBy] = useState<"project" | "date">("project");

  const fetchArchived = useCallback(async () => {
    try {
      const [tasksRes, projectsRes] = await Promise.all([
        fetch("/api/projects"),
        fetch("/api/archived-projects"),
      ]);

      if (tasksRes.ok) {
        const data = await tasksRes.json();
        const projects: Project[] = data.projects || [];

        const archived: ArchivedTaskWithProject[] = [];
        for (const project of projects) {
          for (const task of project.tasks) {
            if (task.archived_at) {
              archived.push({
                ...task,
                projectName: project.name,
                projectTitle: project.title,
                repoPath: project.repo_path,
              });
            }
          }
        }

        archived.sort((a, b) => {
          const dateA = new Date(a.archived_at!).getTime();
          const dateB = new Date(b.archived_at!).getTime();
          return dateB - dateA;
        });

        setArchivedTasks(archived);
      }

      if (projectsRes.ok) {
        const data = await projectsRes.json();
        setArchivedProjects(data.projects || []);
      }
    } catch (e) {
      console.error("Failed to fetch archived:", e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchArchived();
  }, [fetchArchived]);

  // 프로젝트별 그룹핑
  const groupedByProject = archivedTasks.reduce((acc, task) => {
    if (!acc[task.projectName]) {
      acc[task.projectName] = {
        title: task.projectTitle,
        tasks: [],
      };
    }
    acc[task.projectName].tasks.push(task);
    return acc;
  }, {} as Record<string, { title?: string; tasks: ArchivedTaskWithProject[] }>);

  // 날짜별 그룹핑 (YYYY-MM-DD)
  const groupedByDate = archivedTasks.reduce((acc, task) => {
    const date = task.archived_at!.split("T")[0];
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(task);
    return acc;
  }, {} as Record<string, ArchivedTaskWithProject[]>);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400">로딩 중...</div>
      </div>
    );
  }

  const totalCount = archivedTasks.length + archivedProjects.length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link
            href="/projects"
            className="text-gray-400 hover:text-gray-200 transition"
          >
            ← Projects
          </Link>
          <h1 className="text-2xl font-bold text-gray-100">Archive</h1>
          <span className="text-sm text-gray-500">
            ({totalCount} items)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">그룹:</span>
          <button
            onClick={() => setGroupBy("project")}
            className={`px-2 py-1 text-xs rounded transition ${
              groupBy === "project"
                ? "bg-brand-500 text-white"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            프로젝트
          </button>
          <button
            onClick={() => setGroupBy("date")}
            className={`px-2 py-1 text-xs rounded transition ${
              groupBy === "date"
                ? "bg-brand-500 text-white"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            날짜
          </button>
        </div>
      </div>

      {/* 아카이브된 프로젝트 */}
      {archivedProjects.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-medium text-gray-400 mb-3">
            아카이브된 프로젝트 ({archivedProjects.length})
          </h2>
          <div className="space-y-2">
            {archivedProjects.map((project) => (
              <div
                key={project.name}
                className="p-4 bg-gray-900 rounded-xl border border-gray-800 flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-300">
                      {project.title || project.name}
                    </span>
                    <span className="text-xs text-gray-500">{project.machine}</span>
                    <span className="text-xs text-gray-600">
                      {project.task_count} tasks
                    </span>
                  </div>
                  <code className="text-xs text-gray-600">{project.repo_path}</code>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-600">
                    {new Date(project.deleted_at).toLocaleDateString("ko-KR")}
                  </span>
                  <ProjectActions project={project} onUpdated={fetchArchived} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 아카이브된 태스크 */}
      {archivedTasks.length === 0 && archivedProjects.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg mb-2">아카이브된 항목이 없습니다</div>
          <Link
            href="/projects"
            className="text-brand-400 hover:text-brand-300 text-sm"
          >
            프로젝트 목록으로 돌아가기
          </Link>
        </div>
      ) : archivedTasks.length > 0 && (
        <>
          {archivedProjects.length > 0 && (
            <h2 className="text-sm font-medium text-gray-400 mb-3">
              아카이브된 태스크 ({archivedTasks.length})
            </h2>
          )}
          {groupBy === "project" ? (
            <div className="space-y-6">
              {Object.entries(groupedByProject).map(([projectName, { title, tasks }]) => (
                <div
                  key={projectName}
                  className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
                >
                  <div className="p-4 border-b border-gray-800">
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-semibold text-brand-400">
                        {title || projectName}
                      </h2>
                      <span className="text-xs text-gray-500">
                        ({tasks.length} archived)
                      </span>
                    </div>
                  </div>
                  <div className="p-4 space-y-2">
                    {tasks.map((task) => (
                      <div
                        key={`${projectName}-${task.name}`}
                        className="group p-3 bg-gray-800/50 rounded-lg border border-gray-700/50"
                      >
                        <div className="flex items-center gap-2 flex-wrap">
                          <StatusBadge status={task.status} />
                          <span className="font-medium text-gray-300">
                            {task.name}
                          </span>
                          {task.jira_key && (
                            <span className="px-2 py-0.5 bg-gray-700/50 text-gray-500 rounded text-xs">
                              {task.jira_key}
                            </span>
                          )}
                          <span className="text-xs text-gray-600">
                            {new Date(task.archived_at!).toLocaleDateString("ko-KR")}
                          </span>
                          <TaskActions
                            project={projectName}
                            task={task}
                            onUpdated={fetchArchived}
                          />
                        </div>
                        <code className="block mt-1 text-xs text-gray-600 font-mono">
                          {task.branch}
                        </code>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(groupedByDate)
                .sort(([a], [b]) => b.localeCompare(a))
                .map(([date, tasks]) => (
                  <div
                    key={date}
                    className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
                  >
                    <div className="p-4 border-b border-gray-800">
                      <h2 className="text-lg font-semibold text-gray-200">
                        {new Date(date).toLocaleDateString("ko-KR", {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                          weekday: "short",
                        })}
                      </h2>
                    </div>
                    <div className="p-4 space-y-2">
                      {tasks.map((task) => (
                        <div
                          key={`${task.projectName}-${task.name}`}
                          className="group p-3 bg-gray-800/50 rounded-lg border border-gray-700/50"
                        >
                          <div className="flex items-center gap-2 flex-wrap">
                            <StatusBadge status={task.status} />
                            <span className="font-medium text-gray-300">
                              {task.name}
                            </span>
                            <span className="px-2 py-0.5 bg-brand-500/20 text-brand-400 rounded text-xs">
                              {task.projectTitle || task.projectName}
                            </span>
                            {task.jira_key && (
                              <span className="px-2 py-0.5 bg-gray-700/50 text-gray-500 rounded text-xs">
                                {task.jira_key}
                              </span>
                            )}
                            <TaskActions
                              project={task.projectName}
                              task={task}
                              onUpdated={fetchArchived}
                            />
                          </div>
                          <code className="block mt-1 text-xs text-gray-600 font-mono">
                            {task.branch}
                          </code>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
