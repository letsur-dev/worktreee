"use client";

import { Project, Task, BranchSuggestion, PRInfo } from "@/types";
import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

// 클립보드 복사 (Firefox HTTP 환경 fallback 포함)
function copyToClipboard(text: string): Promise<boolean> {
  // 먼저 navigator.clipboard 시도
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text)
      .then(() => true)
      .catch(() => fallbackCopy(text));
  }
  return Promise.resolve(fallbackCopy(text));
}

function fallbackCopy(text: string): boolean {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand("copy");
    return true;
  } catch {
    return false;
  } finally {
    document.body.removeChild(textarea);
  }
}

function CopyButton({ text, label = "📋 path", className = "" }: { text: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`px-1.5 py-0.5 text-xs rounded transition ${
        copied
          ? "text-green-400 bg-green-600/20"
          : "text-gray-400 hover:text-gray-200 hover:bg-gray-700"
      } ${className}`}
      title={text}
    >
      {copied ? "✓ 복사됨" : label}
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  // pending은 레거시 - in_progress와 동일하게 표시
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

// PR 정보 캐시
const prCache = new Map<string, PRInfo>();

function PRBadge({ repoPath, branch }: { repoPath: string; branch: string }) {
  const [prInfo, setPrInfo] = useState<PRInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const cacheKey = `${repoPath}:${branch}`;

  useEffect(() => {
    // 캐시에 있으면 바로 사용
    if (prCache.has(cacheKey)) {
      setPrInfo(prCache.get(cacheKey)!);
      return;
    }

    const fetchPR = async () => {
      setLoading(true);
      try {
        const res = await fetch("/api/pr-info", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo_path: repoPath, branch }),
        });
        const data = await res.json();
        prCache.set(cacheKey, data);
        setPrInfo(data);
      } catch {
        setPrInfo({ error: "Failed" });
      } finally {
        setLoading(false);
      }
    };

    fetchPR();
  }, [repoPath, branch, cacheKey]);

  if (loading) {
    return <span className="text-xs text-gray-500">...</span>;
  }

  if (!prInfo || prInfo.error || !prInfo.number) {
    return null; // PR 없음
  }

  const stateStyles: Record<string, string> = {
    OPEN: "bg-green-600/20 text-green-400 border-green-600/30",
    MERGED: "bg-purple-600/20 text-purple-400 border-purple-600/30",
    CLOSED: "bg-red-600/20 text-red-400 border-red-600/30",
  };

  const reviewStyles: Record<string, string> = {
    APPROVED: "text-green-400",
    CHANGES_REQUESTED: "text-orange-400",
    REVIEW_REQUIRED: "text-yellow-400",
  };

  return (
    <Link
      href={prInfo.url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs hover:opacity-80 transition ${
        stateStyles[prInfo.state || "OPEN"]
      }`}
    >
      <span>PR #{prInfo.number}</span>
      {prInfo.draft && <span className="text-gray-400">(Draft)</span>}
      {prInfo.review_status && (
        <span className={reviewStyles[prInfo.review_status] || ""}>
          {prInfo.review_status === "APPROVED" && "✓"}
          {prInfo.review_status === "CHANGES_REQUESTED" && "✗"}
          {prInfo.review_status === "REVIEW_REQUIRED" && "○"}
        </span>
      )}
    </Link>
  );
}

interface TaskActionsProps {
  project: string;
  task: Task;
  onUpdated: () => void;
}

function TaskActions({ project, task, onUpdated }: TaskActionsProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleArchive = async () => {
    if (!confirm(`'${task.name}' 태스크를 아카이브하시겠습니까?`)) return;
    setIsLoading(true);
    try {
      const res = await fetch("/api/archive-task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, task_name: task.name }),
      });
      if (res.ok) onUpdated();
    } finally {
      setIsLoading(false);
    }
  };

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

  if (task.archived_at) {
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

  return (
    <div className="flex gap-1 ml-auto opacity-0 group-hover:opacity-100 transition-opacity">
      <button
        onClick={handleArchive}
        className="px-2 py-0.5 text-xs text-gray-400 hover:bg-gray-700 rounded transition"
      >
        아카이브
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

interface NewTaskModalProps {
  project: Project;
  onClose: () => void;
  onCreated: () => void;
}

interface CreateResult {
  task_name: string;
  worktree_path: string;
  claude_command: string | null;
}

function NewTaskModal({ project, onClose, onCreated }: NewTaskModalProps) {
  const [description, setDescription] = useState("");
  const [suggestions, setSuggestions] = useState<BranchSuggestion[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);
  const [detectedJiraKeys, setDetectedJiraKeys] = useState<string[]>([]);
  const [detectedNotionUrls, setDetectedNotionUrls] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createResult, setCreateResult] = useState<CreateResult | null>(null);

  const handleSuggest = async () => {
    if (!description.trim()) return;

    setIsLoading(true);
    setError(null);
    setSuggestions([]);
    setSelectedBranch(null);

    try {
      const res = await fetch("/api/suggest-branch-names", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project: project.name, description }),
      });
      const data = await res.json();
      setSuggestions(data.suggestions || []);
      setDetectedJiraKeys(data.detected_jira_keys || []);
      setDetectedNotionUrls(data.detected_notion_urls || []);
      if (data.suggestions?.length > 0) {
        setSelectedBranch(data.suggestions[0].full);
      }
    } catch (e) {
      setError("추천을 가져오는데 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!selectedBranch) return;

    setIsCreating(true);
    setError(null);

    try {
      const res = await fetch("/api/create-task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project: project.name,
          branch: selectedBranch,
          description,
        }),
      });
      const data = await res.json();

      if (data.success) {
        onCreated();
        setCreateResult({
          task_name: data.task_name,
          worktree_path: data.worktree_path,
          claude_command: data.claude_command,
        });
      } else {
        setError(data.error || "생성에 실패했습니다.");
      }
    } catch (e) {
      setError("생성에 실패했습니다.");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-gray-900 rounded-xl p-6 w-[500px] border border-gray-700 shadow-2xl">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-100">New Task</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition"
          >
            ✕
          </button>
        </div>

        {/* 성공 화면 */}
        {createResult ? (
          <div className="space-y-4">
            <div className="p-4 bg-green-600/10 border border-green-600/30 rounded-lg">
              <div className="text-green-400 font-medium mb-2">태스크가 생성되었습니다!</div>
              <div className="text-sm text-gray-300 space-y-1">
                <div>태스크: <span className="text-gray-100 font-mono">{createResult.task_name}</span></div>
                <div>워크트리: <span className="text-gray-100 font-mono text-xs">{createResult.worktree_path}</span></div>
              </div>
            </div>

            {createResult.claude_command && (
              <div className="p-4 bg-brand-500/10 border border-brand-500/30 rounded-lg">
                <div className="text-brand-400 font-medium mb-2">
                  Claude 세션 (백그라운드에서 시작 중...)
                </div>
                <div className="text-xs text-gray-400 mb-2">
                  레포 분석이 완료되면 --continue로 바로 작업 가능
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-2 bg-gray-800 rounded text-sm text-gray-100 font-mono overflow-x-auto">
                    {createResult.claude_command}
                  </code>
                  <CopyButton
                    text={createResult.claude_command!}
                    label="복사"
                    className="px-3 py-2 text-sm"
                  />
                </div>
              </div>
            )}

            <button
              onClick={onClose}
              className="w-full px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm font-medium transition"
            >
              닫기
            </button>
          </div>
        ) : (
          <>
        <div className="text-sm text-gray-400 mb-4">
          프로젝트: <span className="text-brand-400">{project.title || project.name}</span>
        </div>

        <div className="mb-4">
          <label className="block text-sm text-gray-300 mb-2">작업 설명</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="예: PRDEL-123 사용자 로그인 기능 추가&#10;(Jira 키, Notion URL 자동 감지)"
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-500 resize-none"
            rows={3}
          />
        </div>

        <button
          onClick={handleSuggest}
          disabled={!description.trim() || isLoading}
          className="w-full mb-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
        >
          {isLoading ? "추천 중..." : "브랜치 이름 추천받기"}
        </button>

        {/* 감지된 링크 표시 */}
        {(detectedJiraKeys.length > 0 || detectedNotionUrls.length > 0) && (
          <div className="mb-4 p-3 bg-blue-600/10 border border-blue-600/30 rounded-lg">
            <div className="text-xs text-blue-400 font-medium mb-2">자동 감지된 링크</div>
            <div className="flex flex-wrap gap-2">
              {detectedJiraKeys.map((key) => (
                <a
                  key={key}
                  href={`https://letsur.atlassian.net/browse/${key}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2 py-1 bg-blue-600/20 text-blue-400 rounded text-xs hover:bg-blue-600/30 transition"
                >
                  Jira: {key}
                </a>
              ))}
              {detectedNotionUrls.map((url) => (
                <a
                  key={url}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2 py-1 bg-purple-600/20 text-purple-400 rounded text-xs hover:bg-purple-600/30 transition max-w-[200px] truncate"
                >
                  Notion
                </a>
              ))}
            </div>
          </div>
        )}

        {suggestions.length > 0 && (
          <div className="mb-4 space-y-2">
            <label className="block text-sm text-gray-300 mb-2">추천 브랜치</label>
            {suggestions.map((s) => (
              <label
                key={s.full}
                className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition ${
                  selectedBranch === s.full
                    ? "bg-brand-500/20 border border-brand-500"
                    : "bg-gray-800 border border-gray-700 hover:border-gray-600"
                }`}
              >
                <input
                  type="radio"
                  name="branch"
                  value={s.full}
                  checked={selectedBranch === s.full}
                  onChange={() => setSelectedBranch(s.full)}
                  className="mt-1 accent-brand-500"
                />
                <div className="flex-1">
                  <div className="font-mono text-sm text-gray-100">{s.full}</div>
                  <div className="text-xs text-gray-400 mt-1">{s.reason}</div>
                </div>
              </label>
            ))}
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-error-600/20 border border-error-600 rounded-lg text-sm text-error-400">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          {suggestions.length > 0 && (
            <button
              onClick={handleSuggest}
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 rounded-lg text-sm font-medium transition"
            >
              재추천
            </button>
          )}
          <button
            onClick={handleCreate}
            disabled={!selectedBranch || isCreating}
            className="flex-1 px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
          >
            {isCreating ? "생성 중..." : "생성"}
          </button>
        </div>
          </>
        )}
      </div>
    </div>
  );
}

const COLLAPSED_STORAGE_KEY = "pm-collapsed-projects";
const ORDER_STORAGE_KEY = "pm-project-order";

// 프로젝트 순서 로드/저장 함수
const loadOrder = (): string[] => {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(ORDER_STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
};

const saveOrder = (names: string[]) => {
  localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(names));
};

// 저장된 순서대로 프로젝트 정렬
const sortByOrder = (projects: Project[], order: string[]): Project[] => {
  const orderMap = new Map(order.map((name, idx) => [name, idx]));
  return [...projects].sort((a, b) => {
    const aIdx = orderMap.get(a.name) ?? Infinity;
    const bIdx = orderMap.get(b.name) ?? Infinity;
    return aIdx - bIdx;
  });
};

// Sortable 프로젝트 카드 컴포넌트
interface SortableProjectCardProps {
  project: Project;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onNewTask: () => void;
  onTaskUpdated: () => void;
}

function SortableProjectCard({
  project,
  isCollapsed,
  onToggleCollapse,
  onNewTask,
  onTaskUpdated,
}: SortableProjectCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: project.name });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 1 : 0,
  };

  const activeTaskCount = project.tasks.filter((t) => !t.archived_at).length;
  const activeTasks = project.tasks.filter((t) => !t.archived_at);
  const archivedTasks = project.tasks.filter((t) => t.archived_at);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
    >
      <div className="flex justify-between items-start p-5">
        <div className="flex items-center gap-2">
          <button
            className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-gray-700 rounded cursor-grab active:cursor-grabbing transition touch-none"
            {...listeners}
            {...attributes}
            title="드래그하여 순서 변경"
          >
            <svg width="14" height="18" viewBox="0 0 14 18" className="fill-current">
              <circle cx="4" cy="3" r="1.5" />
              <circle cx="10" cy="3" r="1.5" />
              <circle cx="4" cy="9" r="1.5" />
              <circle cx="10" cy="9" r="1.5" />
              <circle cx="4" cy="15" r="1.5" />
              <circle cx="10" cy="15" r="1.5" />
            </svg>
          </button>
          <div
            className="flex items-center gap-3 cursor-pointer hover:bg-gray-800/50 transition rounded-lg px-2 py-1 -ml-2"
            onClick={onToggleCollapse}
          >
            <span
              className={`text-gray-500 transition-transform ${
                isCollapsed ? "" : "rotate-90"
              }`}
            >
              ▶
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-brand-400">
                  {project.title || project.name}
                </h2>
                <span className="text-xs text-gray-500">
                  ({activeTaskCount} tasks)
                </span>
              </div>
              <code className="text-xs text-gray-500">{project.repo_path}</code>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">{project.machine}</span>
          <button
            onClick={onNewTask}
            className="px-3 py-1 bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium rounded-lg transition"
          >
            + New Task
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="px-5 pb-5">
          {activeTasks.length > 0 && (
            <div className="space-y-2">
              {activeTasks.map((task) => (
                <div
                  key={task.name}
                  className="group p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 hover:bg-gray-800 transition"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <StatusBadge status={task.status} />
                    <span className="font-medium text-gray-100">
                      {task.name}
                    </span>
                    {task.jira_key && (
                      <Link
                        href={`/api/graphs/files/${task.jira_key}_graph.html`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-2 py-0.5 bg-blue-600/20 text-blue-400 rounded text-xs hover:bg-blue-600/30 transition"
                        title="Jira Graph 보기"
                      >
                        {task.jira_key}
                      </Link>
                    )}
                    <PRBadge repoPath={project.repo_path} branch={task.branch} />
                    <TaskActions
                      project={project.name}
                      task={task}
                      onUpdated={onTaskUpdated}
                    />
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <code className="text-xs text-gray-500 font-mono">
                      {task.branch}
                    </code>
                    {task.worktree && <CopyButton text={task.worktree} />}
                  </div>
                </div>
              ))}
            </div>
          )}

          {archivedTasks.length > 0 && (
            <details className="mt-4">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">
                아카이브된 태스크 ({archivedTasks.length})
              </summary>
              <div className="mt-2 space-y-2">
                {archivedTasks.map((task) => (
                  <div
                    key={task.name}
                    className="group p-3 bg-gray-900/50 rounded-lg border border-gray-800 opacity-60"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <StatusBadge status={task.status} />
                      <span className="font-medium text-gray-400 line-through">
                        {task.name}
                      </span>
                      {task.jira_key && (
                        <span className="px-2 py-0.5 bg-gray-700/50 text-gray-500 rounded text-xs">
                          {task.jira_key}
                        </span>
                      )}
                      <TaskActions
                        project={project.name}
                        task={task}
                        onUpdated={onTaskUpdated}
                      />
                    </div>
                    <code className="block mt-1 text-xs text-gray-600 font-mono">
                      {task.branch}
                    </code>
                  </div>
                ))}
              </div>
            </details>
          )}

          {activeTasks.length === 0 && archivedTasks.length === 0 && (
            <p className="text-gray-500 text-sm">태스크 없음</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{ count: number } | null>(null);
  const [modalProject, setModalProject] = useState<Project | null>(null);
  const [collapsedProjects, setCollapsedProjects] = useState<Set<string>>(new Set());
  const [storageLoaded, setStorageLoaded] = useState(false);

  // dnd-kit sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // localStorage에서 접힌 상태 로드 (클라이언트에서만)
  useEffect(() => {
    const saved = localStorage.getItem(COLLAPSED_STORAGE_KEY);
    if (saved) {
      setCollapsedProjects(new Set(JSON.parse(saved)));
    }
    setStorageLoaded(true);
  }, []);

  // 저장된 값이 없고 프로젝트가 로드되면 기본적으로 모두 접기
  useEffect(() => {
    if (storageLoaded && projects.length > 0 && !localStorage.getItem(COLLAPSED_STORAGE_KEY)) {
      const allCollapsed = new Set(projects.map(p => p.name));
      setCollapsedProjects(allCollapsed);
      localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify([...allCollapsed]));
    }
  }, [storageLoaded, projects]);

  const toggleCollapse = (projectName: string) => {
    setCollapsedProjects(prev => {
      const next = new Set(prev);
      if (next.has(projectName)) {
        next.delete(projectName);
      } else {
        next.add(projectName);
      }
      localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify([...next]));
      return next;
    });
  };

  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch("/api/projects");
      if (res.ok) {
        const data = await res.json();
        const projectList = data.projects || [];
        // localStorage에서 저장된 순서 로드
        const savedOrder = loadOrder();
        const sorted = sortByOrder(projectList, savedOrder);
        setProjects(sorted);
      }
    } catch (e) {
      console.error("Failed to fetch projects:", e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 드래그 종료 핸들러
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (over && active.id !== over.id) {
        setProjects((items) => {
          const oldIndex = items.findIndex((p) => p.name === active.id);
          const newIndex = items.findIndex((p) => p.name === over.id);
          const newItems = arrayMove(items, oldIndex, newIndex);
          // 새 순서 저장
          saveOrder(newItems.map((p) => p.name));
          return newItems;
        });
      }
    },
    []
  );

  const syncStatuses = async () => {
    setIsSyncing(true);
    setSyncResult(null);
    try {
      const res = await fetch("/api/sync-task-statuses", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setSyncResult({ count: data.count });
        // PR 캐시 초기화 및 프로젝트 다시 로드
        prCache.clear();
        await fetchProjects();
      }
    } catch (e) {
      console.error("Failed to sync statuses:", e);
    } finally {
      setIsSyncing(false);
      // 3초 후 결과 숨기기
      setTimeout(() => setSyncResult(null), 3000);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400">로딩 중...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Projects</h1>
        <div className="flex items-center gap-3">
          {syncResult && (
            <span className="text-xs text-success-400">
              {syncResult.count}개 상태 업데이트됨
            </span>
          )}
          <button
            onClick={syncStatuses}
            disabled={isSyncing}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-gray-200 text-xs font-medium rounded-lg transition flex items-center gap-2"
          >
            {isSyncing ? (
              <>
                <span className="animate-spin">↻</span>
                동기화 중...
              </>
            ) : (
              <>↻ 상태 동기화</>
            )}
          </button>
        </div>
      </div>

      {projects.length === 0 ? (
        <p className="text-gray-400">등록된 프로젝트가 없습니다.</p>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={projects.map((p) => p.name)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-4">
              {projects.map((project) => (
                <SortableProjectCard
                  key={project.name}
                  project={project}
                  isCollapsed={collapsedProjects.has(project.name)}
                  onToggleCollapse={() => toggleCollapse(project.name)}
                  onNewTask={() => setModalProject(project)}
                  onTaskUpdated={fetchProjects}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      {modalProject && (
        <NewTaskModal
          project={modalProject}
          onClose={() => setModalProject(null)}
          onCreated={() => fetchProjects()}
        />
      )}
    </div>
  );
}
