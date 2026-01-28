export interface Task {
  name: string;
  branch: string;
  // 상태는 PR 기반으로 자동 결정됨:
  // - in_progress: PR 없음 또는 draft PR
  // - in_review: PR open (not draft)
  // - completed: PR merged
  // - pending: 레거시 (in_progress로 표시)
  status: "pending" | "in_progress" | "in_review" | "completed";
  jira_key?: string;
  context?: string;
  worktree?: string;
  created?: string;
  archived_at?: string;
  pr?: PRInfo;  // sync 시 저장된 PR 정보
}

export interface Project {
  name: string;
  repo_path: string;
  machine: string;
  title?: string;
  task_count: number;
  tasks: Task[];
}

export interface Graph {
  filename: string;
  issue_key: string;
  title?: string;
}

export interface BranchSuggestion {
  type: string;
  name: string;
  full: string;
  reason: string;
}

export interface PRInfo {
  number?: number;
  state?: string;  // OPEN, MERGED, CLOSED
  url?: string;
  title?: string;
  draft?: boolean;
  review_status?: string;  // APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED
  error?: string;
}
