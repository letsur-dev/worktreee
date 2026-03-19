#!/usr/bin/env bun

import { bold, cyan, dim, gray, red, yellow } from "./lib/colors";

const VERSION = "0.1.0";

const COMMANDS: Record<string, { desc: string; aliases?: string[] }> = {
  add: { desc: "Register current repo as a project" },
  create: { desc: "Create a new task with worktree" },
  handoff: { desc: "Read/write .handoff/latest.md context", aliases: ["ho"] },
  list: { desc: "List all projects and tasks", aliases: ["ls"] },
  go: { desc: "Navigate to a task worktree", aliases: ["switch", "sw"] },
  status: { desc: "Show current task/project status", aliases: ["st"] },
  pin: { desc: "Jump to a pinned task", aliases: ["p"] },
  archive: { desc: "Archive a task" },
  delete: { desc: "Delete a task and its worktree", aliases: ["rm"] },
  sync: { desc: "Sync projects and task statuses" },
  pr: { desc: "Show PR info for a task" },
  doctor: { desc: "Check system health" },
  init: { desc: "Setup shell wrapper function" },
};

function printHelp() {
  console.log(`
${bold("wte")} ${dim(`v${VERSION}`)} — Worktreee CLI

${bold("Usage:")}
  wte <command> [options]

${bold("Commands:")}`);

  for (const [name, { desc, aliases }] of Object.entries(COMMANDS)) {
    const aliasStr = aliases?.length ? dim(` (${aliases.join(", ")})`) : "";
    console.log(`  ${cyan(name.padEnd(12))}${desc}${aliasStr}`);
  }

  console.log(`
${bold("Options:")}
  ${cyan("--help, -h")}    Show help
  ${cyan("--version, -v")} Show version

${bold("Environment:")}
  ${cyan("WT_API_URL")}    API base URL (default: http://localhost:8000)
`);
}

// Resolve aliases to canonical command names
function resolveCommand(name: string): string | undefined {
  if (COMMANDS[name]) return name;
  for (const [cmd, { aliases }] of Object.entries(COMMANDS)) {
    if (aliases?.includes(name)) return cmd;
  }
  return undefined;
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
    printHelp();
    return;
  }

  if (args.includes("--version") || args.includes("-v")) {
    console.log(VERSION);
    return;
  }

  const cmdName = args[0];
  const resolved = resolveCommand(cmdName);

  if (!resolved) {
    console.error(`${red("error:")} Unknown command '${cmdName}'. Run ${cyan("wte --help")} for usage.`);
    process.exit(1);
  }

  const cmdArgs = args.slice(1);

  try {
    const mod = await import(`./commands/${resolved}.ts`);
    await mod.default(cmdArgs);
  } catch (err: unknown) {
    if (err instanceof Error && "code" in err && (err as NodeJS.ErrnoException).code === "ERR_MODULE_NOT_FOUND") {
      console.error(`${red("error:")} Command '${resolved}' not implemented yet.`);
      process.exit(1);
    }
    if (err instanceof Error && err.message.includes("fetch")) {
      console.error(`${red("error:")} Cannot connect to API. Is the server running?`);
      console.error(dim(`  Run: ${yellow("wte doctor")} to diagnose`));
      process.exit(1);
    }
    throw err;
  }
}

main().catch((err) => {
  console.error(`${red("error:")} ${err.message || err}`);
  process.exit(1);
});
