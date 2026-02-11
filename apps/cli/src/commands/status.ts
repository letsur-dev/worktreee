import { listProjects } from "../api";
import { detectContext } from "../lib/context";
import { bold, cyan, dim, gray, green, yellow, blue, red } from "../lib/colors";
import { symbols } from "../lib/colors";

const STATUS_DISPLAY: Record<string, { color: (s: string) => string; label: string }> = {
  pending: { color: yellow, label: "In Progress" },
  in_progress: { color: yellow, label: "In Progress" },
  in_review: { color: blue, label: "In Review" },
  completed: { color: green, label: "Completed" },
};

export default async function status(args: string[]) {
  const cwd = process.cwd();
  const projects = await listProjects();
  const ctx = detectContext(cwd, projects);

  if (ctx.task && ctx.project) {
    // Inside a task worktree — show task detail
    const t = ctx.task;
    const p = ctx.project;
    const s = STATUS_DISPLAY[t.status] || STATUS_DISPLAY.in_progress;

    console.log();
    console.log(bold(`${p.title || p.name} / ${t.name}`));
    console.log();
    console.log(`  Status:    ${s.color(s.label)}`);
    console.log(`  Branch:    ${cyan(t.branch)}`);
    if (t.worktree) console.log(`  Worktree:  ${dim(t.worktree)}`);
    if (t.jira_key) console.log(`  Jira:      ${t.jira_key}`);
    if (t.context) console.log(`  Context:   ${dim(t.context)}`);

    if (t.pr?.number) {
      const prState = t.pr.state || "OPEN";
      const prColor = prState === "MERGED" ? green : prState === "OPEN" ? cyan : red;
      console.log(`  PR:        ${prColor(`#${t.pr.number} ${prState}`)}${t.pr.draft ? dim(" (draft)") : ""}`);
      if (t.pr.url) console.log(`             ${dim(t.pr.url)}`);
      if (t.pr.review_status) console.log(`  Review:    ${t.pr.review_status}`);
    }

    if (t.created) console.log(`  Created:   ${dim(t.created)}`);
    console.log();
  } else if (ctx.project) {
    // Inside a project repo — show project summary
    const p = ctx.project;
    const active = p.tasks.filter((t) => !t.archived_at);
    const byStatus: Record<string, number> = {};
    for (const t of active) {
      const s = t.status === "pending" ? "in_progress" : t.status;
      byStatus[s] = (byStatus[s] || 0) + 1;
    }

    console.log();
    console.log(bold(cyan(p.title || p.name)));
    console.log(`  ${dim(p.repo_path)} ${dim(`[${p.machine}]`)}`);
    console.log(`  Tasks: ${active.length} active`);
    for (const [s, count] of Object.entries(byStatus)) {
      const display = STATUS_DISPLAY[s] || STATUS_DISPLAY.in_progress;
      console.log(`    ${display.color(display.label)}: ${count}`);
    }
    console.log();
  } else {
    console.log(dim("Not inside a known project or task worktree."));
    console.log(dim(`  cwd: ${cwd}`));
    console.log(dim(`  Run ${cyan("wte list")} to see all projects.`));
  }
}
