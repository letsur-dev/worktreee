import { listProjects, deleteTask } from "../api";
import { fuzzyMatchTasks } from "../lib/context";
import { bold, dim, green, red, yellow } from "../lib/colors";
import { input, select } from "../lib/prompt";

export default async function del(args: string[]) {
  const query = args.join(" ").trim();
  if (!query) {
    console.error(red("Usage: wte delete <task-name>"));
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
      message: "Multiple matches — select task to delete",
      options: matches.map((m) => ({
        label: `${m.project.name}/${m.task.name}`,
        value: m,
        hint: m.task.branch,
      })),
    });
  }

  const { project, task } = match;

  console.log(yellow(`  ⚠ This will permanently delete '${bold(task.name)}' and its worktree.`));
  const confirmation = await input(`Type '${task.name}' to confirm`);

  if (confirmation !== task.name) {
    console.log(dim("  Cancelled."));
    return;
  }

  const result = await deleteTask(project.name, task.name);
  if (result.success) {
    console.log(green(`  ✓ Deleted: ${bold(task.name)}`));
  } else {
    console.error(red(`  ✗ ${result.error}`));
    process.exit(1);
  }
}
