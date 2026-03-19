import type { Project, BranchSuggestion, PRInfo } from "./types";

const BASE = process.env.WT_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

function post<T>(path: string, body: Record<string, unknown>): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ─── Projects ───

export async function listProjects(): Promise<Project[]> {
  const data = await request<{ projects: Project[] }>("/api/projects");
  return data.projects;
}

// ─── Branch Suggestions ───

export async function suggestBranchNames(
  project: string,
  description: string,
): Promise<{
  suggestions: BranchSuggestion[];
  detected_jira_keys: string[];
  detected_notion_urls: string[];
}> {
  return post("/api/suggest-branch-names", { project, description });
}

// ─── Task Create (SSE stream) ───

export function createTaskStream(params: {
  project: string;
  branch: string;
  description: string;
  base_branch?: string;
}): Promise<Response> {
  const qs = new URLSearchParams({
    project: params.project,
    branch: params.branch,
    description: params.description,
  });
  if (params.base_branch) qs.set("base_branch", params.base_branch);
  return fetch(`${BASE}/api/create-task-stream?${qs.toString()}`);
}

// ─── Task Actions ───

export async function archiveTask(
  project: string,
  task_name: string,
): Promise<{ success: boolean; error?: string }> {
  return post("/api/archive-task", { project, task_name });
}

export async function deleteTask(
  project: string,
  task_name: string,
): Promise<{ success: boolean; error?: string }> {
  return post("/api/delete-task", { project, task_name });
}

// ─── Sync ───

export async function syncProjects(): Promise<{
  success: boolean;
  synced: number;
  total: number;
  results: Array<{ project: string; success?: boolean; error?: string }>;
}> {
  return post("/api/sync-projects", {});
}

export async function syncTaskStatuses(): Promise<{
  success: boolean;
  updated: Array<{ project: string; task: string; old: string; new: string }>;
  count: number;
}> {
  return post("/api/sync-task-statuses", {});
}

// ─── PR Info ───

export async function getPRInfo(
  repo_path: string,
  branch: string,
): Promise<PRInfo> {
  return post("/api/pr-info", { repo_path, branch });
}

// ─── Pin Task ───

export async function pinTask(
  project: string,
  task_name: string,
): Promise<{ success: boolean; message?: string; error?: string }> {
  return post("/api/pin-task", { project, task_name });
}

// ─── Add Project ───

export async function addProject(
  repo_path: string,
  machine: string,
  title?: string,
): Promise<{ success: boolean; project?: string; error?: string }> {
  return post("/api/add-project", { repo_path, machine, title });
}

// ─── Health ───

export async function healthCheck(): Promise<boolean> {
  try {
    const data = await request<{ status: string }>("/health");
    return data.status === "healthy";
  } catch {
    return false;
  }
}
