export interface Task {
  name: string;
  branch: string;
  status: "pending" | "in_progress" | "in_review" | "completed";
  jira_key?: string;
  context?: string;
  worktree?: string;
  created?: string;
  archived_at?: string;
  pr?: PRInfo;
}

export interface Project {
  name: string;
  repo_path: string;
  machine: string;
  title?: string;
  task_count: number;
  tasks: Task[];
}

export interface BranchSuggestion {
  type: string;
  name: string;
  full: string;
  reason: string;
}

export interface PRInfo {
  number?: number;
  state?: string;
  url?: string;
  title?: string;
  draft?: boolean;
  review_status?: string;
  error?: string;
}
