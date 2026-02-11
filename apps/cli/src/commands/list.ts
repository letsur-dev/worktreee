import { listProjects } from "../api";
import { bold, cyan, dim, gray, green, yellow, blue, red } from "../lib/colors";

const STATUS_COLORS: Record<string, (s: string) => string> = {
  pending: yellow,
  in_progress: yellow,
  in_review: blue,
  completed: green,
};

const STATUS_LABELS: Record<string, string> = {
  pending: "progress",
  in_progress: "progress",
  in_review: "review",
  completed: "done",
};

export default async function list(args: string[]) {
  const showAll = args.includes("--all") || args.includes("-a");
  const projectFilter = (() => {
    const idx = args.indexOf("--project");
    if (idx >= 0 && args[idx + 1]) return args[idx + 1];
    const pIdx = args.indexOf("-p");
    if (pIdx >= 0 && args[pIdx + 1]) return args[pIdx + 1];
    return null;
  })();

  const projects = await listProjects();

  if (projects.length === 0) {
    console.log(dim("No projects found."));
    return;
  }

  for (const project of projects) {
    if (projectFilter && project.name !== projectFilter) continue;

    const tasks = showAll
      ? project.tasks
      : project.tasks.filter((t) => !t.archived_at);

    const title = project.title || project.name;
    const machine = dim(`[${project.machine}]`);
    console.log(`\n${bold(cyan(title))} ${machine} ${dim(project.repo_path)}`);

    if (tasks.length === 0) {
      console.log(dim("  No tasks"));
      continue;
    }

    for (const task of tasks) {
      const statusFn = STATUS_COLORS[task.status] || gray;
      const statusLabel = STATUS_LABELS[task.status] || task.status;
      const status = statusFn(statusLabel.padEnd(8));

      const pr = task.pr?.number ? dim(` PR#${task.pr.number}`) : "";
      const archived = task.archived_at ? dim(" [archived]") : "";
      const jira = task.jira_key ? dim(` ${task.jira_key}`) : "";

      console.log(`  ${status} ${bold(task.name)}${jira}${pr}${archived}`);
      console.log(`           ${dim(task.branch)}`);
    }
  }

  console.log();
}
