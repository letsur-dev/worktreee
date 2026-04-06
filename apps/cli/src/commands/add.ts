import { addProject, listProjects } from "../api";
import { bold, cyan, dim, green, red, yellow } from "../lib/colors";
import { input, select, confirm } from "../lib/prompt";
import { execSync } from "child_process";

function getGitRoot(cwd: string): string | null {
  try {
    return execSync("git rev-parse --show-toplevel", {
      cwd,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    }).trim();
  } catch {
    return null;
  }
}

function detectMachine(): string {
  const hostname = require("os").hostname();
  // NUC에서 실행 중이면 nuc, 아니면 mac
  if (hostname.toLowerCase().includes("nuc")) return "nuc";
  return process.platform === "darwin" ? "mac" : "nuc";
}

export default async function add(args: string[]) {
  const cwd = process.cwd();
  const gitRoot = args[0] || getGitRoot(cwd);

  if (!gitRoot) {
    console.error(red("error: 현재 디렉토리가 Git 레포가 아닙니다."));
    console.error(dim("  Git 레포 안에서 실행하거나, 경로를 인자로 전달하세요:"));
    console.error(dim("  wte add /path/to/repo"));
    process.exit(1);
  }

  const machine = detectMachine();
  const repoName = require("path").basename(gitRoot);

  // 이미 같은 경로로 등록된 프로젝트인지 확인
  const projects = await listProjects();
  const existing = projects.find((p) => p.repo_path === gitRoot);
  if (existing) {
    console.log(yellow(`'${existing.name}'은(는) 이미 등록되어 있습니다.`));
    console.log(dim(`  ${existing.repo_path} [${existing.machine}]`));
    return;
  }

  console.log(dim(`  Repo: ${gitRoot}`));
  console.log(dim(`  Machine: ${machine}`));

  const result = await addProject(gitRoot, machine);

  if (result.success) {
    console.log(green(`✓ 프로젝트 '${result.project}' 등록 완료`));
  } else {
    console.error(red(`✗ ${result.error}`));
    process.exit(1);
  }
}
