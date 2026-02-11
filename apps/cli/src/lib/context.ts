import type { Project, Task } from "../types";

/**
 * Detect current project and task from cwd by matching against known projects.
 */
export function detectContext(
  cwd: string,
  projects: Project[],
): { project?: Project; task?: Task } {
  for (const project of projects) {
    // Check worktree paths first (more specific)
    for (const task of project.tasks) {
      if (task.worktree && cwd.startsWith(task.worktree)) {
        return { project, task };
      }
    }
    // Check repo_path
    if (cwd.startsWith(project.repo_path) || cwd === project.repo_path) {
      return { project };
    }
  }
  return {};
}

/**
 * Fuzzy match a query against task names (substring, case-insensitive).
 * Returns all matching tasks with their project.
 */
export function fuzzyMatchTasks(
  query: string,
  projects: Project[],
): Array<{ project: Project; task: Task }> {
  const q = query.toLowerCase();
  const results: Array<{ project: Project; task: Task }> = [];

  for (const project of projects) {
    for (const task of project.tasks) {
      if (task.archived_at) continue;
      const name = task.name.toLowerCase();
      const branch = task.branch.toLowerCase();
      if (name.includes(q) || branch.includes(q)) {
        results.push({ project, task });
      }
    }
  }

  return results;
}
