import { listProjects, getPRInfo } from "../api";
import { detectContext, fuzzyMatchTasks } from "../lib/context";
import { bold, cyan, dim, green, red, yellow } from "../lib/colors";

export default async function pr(args: string[]) {
  const projects = await listProjects();
  let project: typeof projects[0] | undefined;
  let task: typeof projects[0]["tasks"][0] | undefined;

  if (args[0]) {
    // Fuzzy match by argument
    const matches = fuzzyMatchTasks(args[0], projects);
    if (matches.length === 0) {
      console.error(red(`No task matching '${args[0]}'`));
      process.exit(1);
    }
    project = matches[0].project;
    task = matches[0].task;
  } else {
    // Auto-detect from cwd
    const ctx = detectContext(process.cwd(), projects);
    project = ctx.project;
    task = ctx.task;
  }

  if (!project || !task) {
    console.error(red("Could not determine task. Specify a task name or run from a worktree."));
    process.exit(1);
  }

  console.log(dim(`Fetching PR info for ${bold(task.branch)}...`));

  const pr = await getPRInfo(project.repo_path, task.branch);

  if (!pr.number) {
    console.log(yellow("No PR found for this branch."));
    return;
  }

  const stateColor = pr.state === "MERGED" ? green : pr.state === "OPEN" ? cyan : red;

  console.log();
  console.log(bold(`PR #${pr.number}`) + ` ${stateColor(pr.state || "UNKNOWN")}`);
  if (pr.title) console.log(`  ${pr.title}`);
  if (pr.draft) console.log(dim("  (Draft)"));
  if (pr.url) console.log(`  ${dim(pr.url)}`);
  if (pr.review_status) {
    const reviewColor =
      pr.review_status === "APPROVED" ? green :
      pr.review_status === "CHANGES_REQUESTED" ? red : yellow;
    console.log(`  Review: ${reviewColor(pr.review_status)}`);
  }
  console.log();
}
