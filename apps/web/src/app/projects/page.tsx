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

// PR 배지 (저장된 PR 정보 사용)
function PRBadge({ pr }: { pr?: PRInfo | null }) {
  if (!pr || !pr.number) {
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
      href={pr.url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs hover:opacity-80 transition ${
        stateStyles[pr.state || "OPEN"]
      }`}
    >
      <span>PR #{pr.number}</span>
      {pr.draft && <span className="text-gray-400">(Draft)</span>}
      {pr.review_status && (
        <span className={reviewStyles[pr.review_status] || ""}>
          {pr.review_status === "APPROVED" && "✓"}
          {pr.review_status === "CHANGES_REQUESTED" && "✗"}
          {pr.review_status === "REVIEW_REQUIRED" && "○"}
        </span>
      )}
    </Link>
  );
}

interface ConfirmModalProps {
  title: string;
  message: string;
  confirmText?: string;
  confirmColor?: "red" | "blue";
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmModal({ title, message, confirmText = "확인", confirmColor = "blue", onConfirm, onCancel }: ConfirmModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onCancel}>
      <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4 shadow-xl" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
        <p className="text-gray-300 mb-6 whitespace-pre-line">{message}</p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-400 hover:bg-gray-700 rounded transition"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm rounded transition ${
              confirmColor === "red"
                ? "bg-red-600 hover:bg-red-700 text-white"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

interface TaskActionsProps {
  project: string;
  task: Task;
  onUpdated: () => void;
  onOpenIDE: (projectName: string, projectPath: string) => void;
  isOpeningIDE: boolean;
}

function TaskActions({ project, task, onUpdated, onOpenIDE, isOpeningIDE }: TaskActionsProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [confirmAction, setConfirmAction] = useState<"archive" | "delete" | null>(null);

  const executeArchive = async () => {
    setConfirmAction(null);
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

  const executeDelete = async () => {
    setConfirmAction(null);
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
      <>
        {confirmAction === "delete" && (
          <ConfirmModal
            title="태스크 삭제"
            message={`'${task.name}' 태스크를 완전히 삭제하시겠습니까?\n워크트리도 함께 삭제됩니다.`}
            confirmText="삭제"
            confirmColor="red"
            onConfirm={executeDelete}
            onCancel={() => setConfirmAction(null)}
          />
        )}
        <div className="flex gap-1 ml-auto">
          <button
            onClick={handleRestore}
            className="px-2 py-0.5 text-xs text-blue-400 hover:bg-blue-600/20 rounded transition"
          >
            복구
          </button>
          <button
            onClick={() => setConfirmAction("delete")}
            className="px-2 py-0.5 text-xs text-red-400 hover:bg-red-600/20 rounded transition"
          >
            삭제
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      {confirmAction === "archive" && (
        <ConfirmModal
          title="태스크 아카이브"
          message={`'${task.name}' 태스크를 아카이브하시겠습니까?`}
          confirmText="아카이브"
          confirmColor="blue"
          onConfirm={executeArchive}
          onCancel={() => setConfirmAction(null)}
        />
      )}
      {confirmAction === "delete" && (
        <ConfirmModal
          title="태스크 삭제"
          message={`'${task.name}' 태스크를 완전히 삭제하시겠습니까?\n워크트리도 함께 삭제됩니다.`}
          confirmText="삭제"
          confirmColor="red"
          onConfirm={executeDelete}
          onCancel={() => setConfirmAction(null)}
        />
      )}
      <div className="flex gap-1 ml-auto opacity-0 group-hover:opacity-100 transition-opacity">
        {task.worktree && (
          <button
            onClick={() => onOpenIDE(project, task.worktree!)}
            disabled={isOpeningIDE}
            className="px-2 py-0.5 text-xs text-brand-400 hover:bg-brand-600/20 rounded transition disabled:opacity-50"
            title="IntelliJ에서 열기"
          >
            🛋️
          </button>
        )}
        <button
          onClick={() => setConfirmAction("archive")}
          className="px-2 py-0.5 text-xs text-gray-400 hover:bg-gray-700 rounded transition"
        >
          아카이브
        </button>
        <button
          onClick={() => setConfirmAction("delete")}
          className="px-2 py-0.5 text-xs text-red-400 hover:bg-red-600/20 rounded transition"
        >
          삭제
        </button>
      </div>
    </>
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
  const [baseBranch, setBaseBranch] = useState("");  // base 브랜치 또는 PR URL
  const [suggestions, setSuggestions] = useState<BranchSuggestion[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);
  const [detectedJiraKeys, setDetectedJiraKeys] = useState<string[]>([]);
  const [detectedNotionUrls, setDetectedNotionUrls] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [createResult, setCreateResult] = useState<CreateResult | null>(null);
  const [jiraUrl, setJiraUrl] = useState("");

  useEffect(() => {
    fetch("/api/config").then(r => r.json()).then(d => setJiraUrl(d.jira_url || "")).catch(() => {});
  }, []);

  const handleSuggest = async () => {
    if (!description.trim()) return;

    setIsLoading(true);
    setError(null);
    setStreamingMessage(null);
    setWarning(null);
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
    if (!selectedBranch || isCreating) return;

    setIsCreating(true);
    setError(null);
    setWarning(null);
    setStreamingMessage("준비 중...");

    try {
      const params = new URLSearchParams({
        project: project.name,
        branch: selectedBranch,
        description,
        base_branch: baseBranch || "",
      });

      const response = await fetch(`/api/create-task-stream?${params.toString()}`);
      const reader = response.body?.getReader();
      if (!reader) throw new Error("스트림을 읽을 수 없습니다.");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim().startsWith("data: ")) {
            const data = JSON.parse(line.trim().slice(6));
            
            if (data.type === "info") {
              setStreamingMessage(data.message);
            } else if (data.type === "warning") {
              setWarning(data.message);
            } else if (data.type === "error") {
              setError(data.message);
              setIsCreating(false);
              return;
            } else if (data.type === "done") {
              onCreated();
              setCreateResult({
                task_name: data.task_name,
                worktree_path: data.worktree_path,
                claude_command: data.claude_command,
              });
              if (data.warning) setWarning(data.warning);
              setIsCreating(false);
              setStreamingMessage(null);
              return;
            }
          }
        }
      }
    } catch (e) {
      console.error("[create-task] 예외:", e);
      setError("생성 중 오류가 발생했습니다.");
    } finally {
      setIsCreating(false);
      setStreamingMessage(null);
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
                  새 세션에서 자동으로 컨텍스트가 주입됩니다
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

        <div className="mb-4">
          <label className="block text-sm text-gray-300 mb-2">
            Base 브랜치 <span className="text-gray-500">(선택)</span>
          </label>
          <input
            type="text"
            value={baseBranch}
            onChange={(e) => setBaseBranch(e.target.value)}
            placeholder="예: feature/xxx 또는 https://github.com/.../pull/123"
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-500 text-sm"
          />
          <div className="text-xs text-gray-500 mt-1">
            PR URL 입력 시 해당 PR의 브랜치를 base로 사용
          </div>
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
                  href={`${jiraUrl}/browse/${key}`}
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

        {warning && (
          <div className="mb-4 p-3 bg-warning-600/20 border border-warning-600 rounded-lg text-sm text-warning-400">
            ⚠️ {warning}
          </div>
        )}

        {isCreating && streamingMessage && (
          <div className="mb-4 flex items-center gap-2 text-sm text-gray-400 animate-pulse">
            <span className="w-2 h-2 bg-brand-500 rounded-full"></span>
            {streamingMessage}
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

interface NewProjectModalProps {
  onClose: () => void;
  onCreated: () => void;
}

function NewProjectModal({ onClose, onCreated }: NewProjectModalProps) {
  const [repoPath, setRepoPath] = useState("");
  const [machine, setMachine] = useState("nuc");
  const [title, setTitle] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!repoPath.trim() || isCreating) return;

    setIsCreating(true);
    setError(null);

    try {
      const res = await fetch("/api/add-project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_path: repoPath.trim(),
          machine,
          title: title.trim() || null,
        }),
      });
      const data = await res.json();

      if (data.success) {
        onCreated();
        onClose();
      } else {
        setError(data.error || "생성에 실패했습니다.");
      }
    } catch {
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
          <h3 className="text-lg font-semibold text-gray-100">New Project</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">
              Git 레포 경로 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              placeholder="예: ~/Documents/my-project"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-500 text-sm"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">머신</label>
            <select
              value={machine}
              onChange={(e) => setMachine(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:border-brand-500 text-sm"
            >
              <option value="nuc">nuc</option>
              <option value="mac">mac</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">
              표시 제목 <span className="text-gray-500">(선택)</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="예: My Project"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-500 text-sm"
            />
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-error-600/20 border border-error-600 rounded-lg text-sm text-error-400">
            {error}
          </div>
        )}

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition"
          >
            취소
          </button>
          <button
            onClick={handleCreate}
            disabled={!repoPath.trim() || isCreating}
            className="flex-1 px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
          >
            {isCreating ? "생성 중..." : "생성"}
          </button>
        </div>
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

// Git Log 터미널 패널
function GitLogPanel({ projectName }: { projectName: string }) {
  const [log, setLog] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLog = async () => {
      setLoading(true);
      try {
        const res = await fetch("/api/git-log", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project: projectName, limit: 20 }),
        });
        const data = await res.json();
        if (data.success) {
          setLog(data.log);
        } else {
          setError(data.error);
        }
      } catch {
        setError("Failed to fetch git log");
      } finally {
        setLoading(false);
      }
    };
    fetchLog();
  }, [projectName]);

  if (loading) {
    return (
      <div className="bg-gray-950 rounded-lg p-4 font-mono text-xs text-gray-500">
        Loading git log...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-950 rounded-lg p-4 font-mono text-xs text-red-400">
        Error: {error}
      </div>
    );
  }

  // 색상 파싱: 브랜치 이름, 커밋 해시 등
  const colorize = (line: string) => {
    // 그래프 문자: * | / \
    // 커밋 해시: 7자 영숫자
    // 브랜치 이름: (HEAD -> develop, origin/develop)

    return line
      .replace(/^([*|\\\/\s]+)/, '<span class="text-yellow-500">$1</span>') // 그래프
      .replace(/\b([a-f0-9]{7,8})\b/, '<span class="text-green-400">$1</span>') // 해시
      .replace(/\(([^)]+)\)/, '<span class="text-cyan-400">($1)</span>'); // 브랜치/태그
  };

  return (
    <div className="bg-gray-950 rounded-lg p-4 font-mono text-xs overflow-x-auto max-h-80 overflow-y-auto">
      <pre className="text-gray-300 leading-relaxed">
        {log?.split('\n').map((line, i) => (
          <div
            key={i}
            dangerouslySetInnerHTML={{ __html: colorize(line) }}
            className="hover:bg-gray-900/50"
          />
        ))}
      </pre>
    </div>
  );
}

// Sortable 프로젝트 카드 컴포넌트
interface SortableProjectCardProps {
  project: Project;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onNewTask: () => void;
  onTaskUpdated: () => void;
  onOpenIDE: (projectName: string, projectPath: string) => void;
  isOpeningIDE: boolean;
}

function SortableProjectCard({
  project,
  isCollapsed,
  onToggleCollapse,
  onNewTask,
  onTaskUpdated,
  onOpenIDE,
  isOpeningIDE,
}: SortableProjectCardProps) {
  const [showGitLog, setShowGitLog] = useState(false);

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
            onClick={() => setShowGitLog(!showGitLog)}
            className={`px-3 py-1 text-xs font-medium rounded-lg transition ${
              showGitLog
                ? "bg-green-600 hover:bg-green-700 text-white"
                : "bg-gray-700 hover:bg-gray-600 text-gray-300"
            }`}
            title="Git 로그 보기"
          >
            🌲 Git
          </button>
          <button
            onClick={() => onOpenIDE(project.name, project.repo_path)}
            disabled={isOpeningIDE}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-medium rounded-lg transition disabled:opacity-50"
            title="IntelliJ에서 열기 (JetBrains Gateway)"
          >
            {isOpeningIDE ? "..." : "🛋️ IDE"}
          </button>
          <button
            onClick={onNewTask}
            className="px-3 py-1 bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium rounded-lg transition"
          >
            + New Task
          </button>
        </div>
      </div>

      {showGitLog && (
        <div className="px-5 pb-3">
          <GitLogPanel projectName={project.name} />
        </div>
      )}

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
                    <PRBadge pr={task.pr} />
                    <TaskActions
                      project={project.name}
                      task={task}
                      onUpdated={onTaskUpdated}
                      onOpenIDE={onOpenIDE}
                      isOpeningIDE={isOpeningIDE}
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
  const [isSyncingProjects, setIsSyncingProjects] = useState(false);
  const [syncProjectsResult, setSyncProjectsResult] = useState<{ synced: number; total: number } | null>(null);
  const [modalProject, setModalProject] = useState<Project | null>(null);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [collapsedProjects, setCollapsedProjects] = useState<Set<string>>(new Set());
  const [storageLoaded, setStorageLoaded] = useState(false);

  // dnd-kit sensors
  const [isOpeningIDE, setIsOpeningIDE] = useState(false);

  const handleOpenIDE = async (projectName: string, projectPath: string) => {
    setIsOpeningIDE(true);
    try {
      const res = await fetch("/api/projects/ide-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          project: projectName,
          project_path: projectPath 
        }),
      });
      const data = await res.json();
      
      if (data.success) {
        if (data.is_local) {
          // Mac 로컬: IntelliJ 직접 호출 스킴
          const url = `idea://open?file=${encodeURIComponent(data.project_path)}`;
          console.log("Opening local IDE:", url);
          window.location.assign(url);
        } else {
          // 원격: JetBrains Gateway 호출 (productCode 사용, Gateway가 IDE 자동 탐지)
          const targetPath = data.project_path || projectPath;
          const scheme = `jetbrains-gateway://connect#type=ssh&host=${data.host}&port=${data.port}&user=${data.user}&productCode=IU&projectPath=${encodeURIComponent(targetPath)}&deploy=false`;
          window.location.href = scheme;
        }
      } else {
        alert(data.error || "IntelliJ를 실행할 수 없습니다.");
      }
    } catch (e) {
      alert("IDE 실행 중 오류가 발생했습니다.");
    } finally {
      setIsOpeningIDE(false);
    }
  };

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
        // 프로젝트 다시 로드 (PR 정보가 sync 시 저장됨)
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

  const syncProjects = async () => {
    setIsSyncingProjects(true);
    setSyncProjectsResult(null);
    try {
      const res = await fetch("/api/sync-projects", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setSyncProjectsResult({ synced: data.synced, total: data.total });
      }
    } catch (e) {
      console.error("Failed to sync projects:", e);
    } finally {
      setIsSyncingProjects(false);
      setTimeout(() => setSyncProjectsResult(null), 3000);
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
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-100">Projects</h1>
          <Link
            href="/projects/archive"
            className="text-sm text-gray-500 hover:text-gray-300 transition"
          >
            Archive →
          </Link>
        </div>
        <div className="flex items-center gap-3">
          {syncProjectsResult && (
            <span className="text-xs text-blue-400">
              {syncProjectsResult.synced}/{syncProjectsResult.total} 레포 동기화됨
            </span>
          )}
          {syncResult && (
            <span className="text-xs text-success-400">
              {syncResult.count}개 상태 업데이트됨
            </span>
          )}
          <button
            onClick={syncProjects}
            disabled={isSyncingProjects}
            className="px-3 py-1.5 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-800 disabled:text-gray-500 text-gray-200 text-xs font-medium rounded-lg transition flex items-center gap-2"
            title="모든 프로젝트 메인 레포를 git pull로 최신화"
          >
            {isSyncingProjects ? (
              <>
                <span className="animate-spin">↻</span>
                Pull 중...
              </>
            ) : (
              <>⬇ Git Pull</>
            )}
          </button>
          <button
            onClick={syncStatuses}
            disabled={isSyncing}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-gray-200 text-xs font-medium rounded-lg transition flex items-center gap-2"
            title="모든 태스크 상태를 PR 기반으로 동기화"
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
          <button
            onClick={() => setShowNewProjectModal(true)}
            className="px-3 py-1.5 bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium rounded-lg transition"
          >
            + New Project
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
                  onOpenIDE={handleOpenIDE}
                  isOpeningIDE={isOpeningIDE}
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

      {showNewProjectModal && (
        <NewProjectModal
          onClose={() => setShowNewProjectModal(false)}
          onCreated={() => fetchProjects()}
        />
      )}
    </div>
  );
}
