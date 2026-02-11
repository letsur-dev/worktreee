import { healthCheck, listProjects } from "../api";
import { bold, cyan, dim, green, red, yellow } from "../lib/colors";
import { existsSync } from "fs";

export default async function doctor(_args: string[]) {
  console.log(bold("\nwte doctor\n"));

  let allOk = true;

  // 1. API connection
  process.stdout.write("  API connection... ");
  const apiUrl = process.env.WT_API_URL || "http://localhost:8000";
  try {
    const healthy = await healthCheck();
    if (healthy) {
      console.log(green("✓") + dim(` ${apiUrl}`));
    } else {
      console.log(red("✗") + dim(` ${apiUrl} (unhealthy)`));
      allOk = false;
    }
  } catch {
    console.log(red("✗") + dim(` ${apiUrl} (unreachable)`));
    allOk = false;
  }

  // 2. Projects & tasks
  try {
    const projects = await listProjects();
    const totalTasks = projects.reduce((sum, p) => sum + p.tasks.length, 0);
    const activeTasks = projects.reduce(
      (sum, p) => sum + p.tasks.filter((t) => !t.archived_at).length,
      0,
    );
    console.log(`  Projects:    ${green("✓")} ${projects.length} projects, ${activeTasks} active tasks (${totalTasks} total)`);

    // 3. Worktree existence check
    let missingWorktrees = 0;
    for (const project of projects) {
      for (const task of project.tasks) {
        if (task.worktree && !task.archived_at) {
          if (!existsSync(task.worktree)) {
            missingWorktrees++;
          }
        }
      }
    }

    if (missingWorktrees > 0) {
      console.log(`  Worktrees:   ${yellow("⚠")} ${missingWorktrees} missing worktree path(s)`);
      allOk = false;
    } else {
      console.log(`  Worktrees:   ${green("✓")} all paths exist`);
    }
  } catch {
    console.log(`  Projects:    ${red("✗")} could not fetch`);
    allOk = false;
  }

  // 4. Shell function check
  const shell = process.env.SHELL || "";
  const home = process.env.HOME || "";
  const rcFile = shell.includes("zsh") ? `${home}/.zshrc` : `${home}/.bashrc`;
  process.stdout.write(`  Shell func:  `);

  try {
    const rc = await Bun.file(rcFile).text();
    if (rc.includes("__WT_CD__")) {
      console.log(green("✓") + dim(` found in ${rcFile}`));
    } else {
      console.log(yellow("⚠") + dim(` not found in ${rcFile}. Run: wte init --install`));
      allOk = false;
    }
  } catch {
    console.log(yellow("⚠") + dim(` could not read ${rcFile}`));
    allOk = false;
  }

  // 5. Bun version
  const bunVersion = Bun.version;
  console.log(`  Bun:         ${green("✓")} v${bunVersion}`);

  console.log();
  if (allOk) {
    console.log(green("  All checks passed!"));
  } else {
    console.log(yellow("  Some checks need attention."));
  }
  console.log();
}
