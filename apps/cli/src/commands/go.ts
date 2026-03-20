import { listProjects } from "../api";
import { fuzzyMatchTasks } from "../lib/context";
import { bold, cyan, dim, red, yellow } from "../lib/colors";
import { select } from "../lib/prompt";
import { requestCd } from "../lib/cd";

export default async function go(args: string[]) {
  const query = args.join(" ").trim();
  if (!query) {
    console.error(red("Usage: wte go <task-name>"));
    process.exit(1);
  }

  const projects = await listProjects();
  const matches = fuzzyMatchTasks(query, projects);

  if (matches.length === 0) {
    console.error(red(`No task matching '${query}'`));
    process.exit(1);
  }

  let match = matches[0];

  if (matches.length > 1) {
    match = await select({
      message: "Multiple matches — select task",
      options: matches.map((m) => ({
        label: `${m.project.name}/${m.task.name}`,
        value: m,
        hint: m.task.branch,
      })),
    });
  }

  const { project, task } = match;

  if (!task.worktree) {
    console.error(yellow(`Task '${task.name}' has no worktree path.`));
    process.exit(1);
  }

  // Warn if remote machine
  const localMachine = process.env.LOCAL_MACHINE || "local";
  if (project.machine !== "local" && project.machine !== localMachine) {
    console.log(yellow(`  ⚠ This worktree is on ${bold(project.machine)}`));
    console.log(dim(`    ssh ${project.machine} -t "cd ${task.worktree} && exec \\$SHELL"`));
  }

  console.log(dim(`  ${project.name}/${task.name}`));
  requestCd(task.worktree);
}
