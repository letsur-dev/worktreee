import { listProjects, archiveTask } from "../api";
import { fuzzyMatchTasks } from "../lib/context";
import { bold, cyan, dim, green, red } from "../lib/colors";
import { confirm, select } from "../lib/prompt";

export default async function archive(args: string[]) {
  const query = args.join(" ").trim();
  if (!query) {
    console.error(red("Usage: wte archive <task-name>"));
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

  const ok = await confirm(`Archive '${task.name}'?`);
  if (!ok) return;

  const result = await archiveTask(project.name, task.name);
  if (result.success) {
    console.log(green(`  ✓ Archived: ${bold(task.name)}`));
  } else {
    console.error(red(`  ✗ ${result.error}`));
    process.exit(1);
  }
}
