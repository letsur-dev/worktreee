import { syncProjects, syncTaskStatuses } from "../api";
import { bold, cyan, dim, green, red, yellow } from "../lib/colors";
import { spinner } from "../lib/prompt";

export default async function sync(args: string[]) {
  // 1. Sync projects (git fetch + pull)
  const spin1 = spinner("Syncing project repos...");
  try {
    const result = await syncProjects();
    spin1.stop(green(`  ✓ Repos synced: ${result.synced}/${result.total}`));

    for (const r of result.results) {
      if (r.error) {
        console.log(red(`    ✗ ${r.project}: ${r.error}`));
      }
    }
  } catch {
    spin1.stop(red("  ✗ Failed to sync repos"));
  }

  // 2. Sync task statuses (PR-based)
  const spin2 = spinner("Syncing task statuses...");
  try {
    const result = await syncTaskStatuses();
    spin2.stop(green(`  ✓ Statuses synced: ${result.count} updated`));

    for (const u of result.updated) {
      console.log(dim(`    ${u.project}/${u.task}: ${u.old} → ${cyan(u.new)}`));
    }
  } catch {
    spin2.stop(red("  ✗ Failed to sync statuses"));
  }

  console.log();
}
