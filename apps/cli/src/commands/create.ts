import { listProjects, suggestBranchNames, createTaskStream } from "../api";
import { detectContext } from "../lib/context";
import { bold, cyan, dim, green, red, yellow } from "../lib/colors";
import { select, input, spinner } from "../lib/prompt";
import { parseSSE } from "../lib/sse";

function extractFlag(args: string[], flag: string): string | undefined {
  const idx = args.indexOf(flag);
  if (idx >= 0 && args[idx + 1]) {
    args.splice(idx, 2);
    return args[idx]; // value was at idx+1, now shifted
  }
  // re-check after splice — actually let's do it differently
  return undefined;
}

function parseArgs(args: string[]): {
  description: string;
  branch?: string;
  project?: string;
  base?: string;
} {
  const flags: Record<string, string> = {};
  const positional: string[] = [];

  for (let i = 0; i < args.length; i++) {
    if ((args[i] === "--branch" || args[i] === "-b") && args[i + 1]) {
      flags.branch = args[++i];
    } else if ((args[i] === "--project" || args[i] === "-p") && args[i + 1]) {
      flags.project = args[++i];
    } else if (args[i] === "--base" && args[i + 1]) {
      flags.base = args[++i];
    } else {
      positional.push(args[i]);
    }
  }

  return {
    description: positional.join(" ").trim(),
    branch: flags.branch,
    project: flags.project,
    base: flags.base,
  };
}

export default async function create(args: string[]) {
  const parsed = parseArgs(args);
  const projects = await listProjects();

  if (projects.length === 0) {
    console.error(red("No projects found. Add a project via the web UI first."));
    process.exit(1);
  }

  // 1. Detect or select project
  const ctx = detectContext(process.cwd(), projects);
  let project = ctx.project;

  if (parsed.project) {
    project = projects.find((p) => p.name === parsed.project);
    if (!project) {
      console.error(red(`Project '${parsed.project}' not found.`));
      process.exit(1);
    }
  }

  if (!project) {
    project = await select({
      message: "Select project",
      options: projects.map((p) => ({
        label: p.title || p.name,
        value: p,
        hint: `${p.machine} · ${p.repo_path}`,
      })),
    });
  } else {
    console.log(dim(`Project: ${project.title || project.name}`));
  }

  // 2. Get description
  let description = parsed.description;
  if (!description) {
    description = await input("Task description");
  }
  if (!description) {
    console.error(red("Description is required."));
    process.exit(1);
  }

  // 3. Get branch — either from flag or suggest interactively
  let branch = parsed.branch;

  if (!branch) {
    const spin = spinner("Generating branch suggestions...");
    let suggestions;
    try {
      const result = await suggestBranchNames(project.name, description);
      suggestions = result.suggestions;
      spin.stop();

      if (result.detected_jira_keys.length > 0) {
        console.log(dim(`  Jira: ${result.detected_jira_keys.join(", ")}`));
      }
      if (result.detected_notion_urls.length > 0) {
        console.log(dim(`  Notion: ${result.detected_notion_urls.length} URL(s) detected`));
      }
    } catch {
      spin.stop();
      console.error(red("Failed to get branch suggestions."));
      process.exit(1);
    }

    if (!suggestions || suggestions.length === 0) {
      console.error(red("No branch suggestions received."));
      process.exit(1);
    }

    branch = await select({
      message: "Select branch",
      options: suggestions.map((s) => ({
        label: s.full,
        value: s.full,
        hint: s.reason,
      })),
    });
  }

  // 4. Create task via SSE stream
  console.log();
  const response = await createTaskStream({
    project: project.name,
    branch,
    description,
    base_branch: parsed.base,
  });

  for await (const event of parseSSE<{
    type: string;
    message?: string;
    success?: boolean;
    task_name?: string;
    worktree_path?: string;
    claude_command?: string;
    warning?: string;
  }>(response)) {
    if (event.type === "info") {
      console.log(dim(`  ${event.message}`));
    } else if (event.type === "warning") {
      console.log(yellow(`  ⚠ ${event.message}`));
    } else if (event.type === "error") {
      console.error(red(`  ✗ ${event.message}`));
      process.exit(1);
    } else if (event.type === "done") {
      console.log();
      console.log(green(`  ✓ Task created: ${bold(event.task_name || "")}`));

      if (event.worktree_path) {
        console.log(dim(`  Worktree: ${event.worktree_path}`));
      }

      if (event.claude_command) {
        console.log(dim(`  Claude: ${event.claude_command}`));
      }

      if (event.warning) {
        console.log(yellow(`  ⚠ ${event.warning}`));
      }

      // Output __WT_CD__ for shell wrapper to detect
      if (event.worktree_path) {
        console.log(`__WT_CD__:${event.worktree_path}`);
      }
    }
  }
}
