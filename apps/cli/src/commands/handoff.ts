import { listProjects } from "../api";
import { detectContext } from "../lib/context";
import { bold, cyan, dim, green, red, yellow } from "../lib/colors";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";

const HANDOFF_DIR = ".handoff";
const HANDOFF_FILE = "latest.md";

function resolveHandoffPath(cwd: string): { path: string; dir: string } | null {
  // .handoff가 있는 디렉토리를 상위로 탐색
  let dir = cwd;
  for (let i = 0; i < 10; i++) {
    if (existsSync(join(dir, ".git")) || existsSync(join(dir, HANDOFF_DIR))) {
      const handoffDir = join(dir, HANDOFF_DIR);
      return { path: join(handoffDir, HANDOFF_FILE), dir: handoffDir };
    }
    const parent = join(dir, "..");
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function printUsage() {
  console.log(`
${bold("wte handoff")} — .handoff/latest.md 관리

${bold("Usage:")}
  wte handoff                   현재 핸드오프 내용 출력
  wte handoff read              위와 동일
  wte handoff write <content>   핸드오프 내용 덮어쓰기
  wte handoff write -           stdin에서 읽어서 쓰기
  wte handoff append <content>  기존 내용에 추가
  wte handoff append -          stdin에서 읽어서 추가
  wte handoff init              빈 핸드오프 파일 생성
  wte handoff path              핸드오프 파일 경로 출력

${bold("Examples:")}
  wte handoff write "## 목표\\n로그인 API 구현"
  cat context.md | wte handoff write -
  wte handoff append "## 진행 상황\\n- API 엔드포인트 완료"
`);
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf-8").trim();
}

export default async function handoff(args: string[]) {
  const cwd = process.cwd();
  const subcommand = args[0] || "read";

  if (subcommand === "--help" || subcommand === "-h") {
    printUsage();
    return;
  }

  const resolved = resolveHandoffPath(cwd);

  if (subcommand === "init") {
    if (!resolved) {
      console.error(red("error: Git 레포 안에서 실행하세요."));
      process.exit(1);
    }
    mkdirSync(resolved.dir, { recursive: true });
    if (!existsSync(resolved.path)) {
      writeFileSync(resolved.path, "# Handoff\n\n## 목표\n\n## 다음 할 것\n", "utf-8");
      console.log(green(`✓ ${resolved.path} 생성됨`));
    } else {
      console.log(dim("이미 존재합니다."));
    }
    return;
  }

  if (subcommand === "path") {
    if (!resolved) {
      console.error(red("error: .handoff 를 찾을 수 없습니다."));
      process.exit(1);
    }
    console.log(resolved.path);
    return;
  }

  if (subcommand === "read") {
    if (!resolved || !existsSync(resolved.path)) {
      console.error(red("error: .handoff/latest.md 가 없습니다."));
      console.error(dim("  wte handoff init 으로 생성하거나, wte create 로 태스크를 만드세요."));
      process.exit(1);
    }
    const content = readFileSync(resolved.path, "utf-8");
    console.log(content);
    return;
  }

  if (subcommand === "write") {
    if (!resolved) {
      console.error(red("error: Git 레포 안에서 실행하세요."));
      process.exit(1);
    }
    let content: string;
    if (args[1] === "-") {
      content = await readStdin();
    } else {
      content = args.slice(1).join(" ");
    }
    if (!content) {
      console.error(red("error: 내용을 입력하세요."));
      console.error(dim("  wte handoff write \"내용\" 또는 echo \"내용\" | wte handoff write -"));
      process.exit(1);
    }
    mkdirSync(resolved.dir, { recursive: true });
    writeFileSync(resolved.path, content.replace(/\\n/g, "\n"), "utf-8");
    console.log(green(`✓ ${resolved.path} 업데이트됨 (${content.length} bytes)`));
    return;
  }

  if (subcommand === "append") {
    if (!resolved) {
      console.error(red("error: Git 레포 안에서 실행하세요."));
      process.exit(1);
    }
    let content: string;
    if (args[1] === "-") {
      content = await readStdin();
    } else {
      content = args.slice(1).join(" ");
    }
    if (!content) {
      console.error(red("error: 내용을 입력하세요."));
      process.exit(1);
    }
    mkdirSync(resolved.dir, { recursive: true });
    const existing = existsSync(resolved.path)
      ? readFileSync(resolved.path, "utf-8")
      : "";
    const newContent = existing + "\n" + content.replace(/\\n/g, "\n") + "\n";
    writeFileSync(resolved.path, newContent, "utf-8");
    console.log(green(`✓ ${resolved.path} 에 추가됨`));
    return;
  }

  console.error(red(`error: 알 수 없는 하위 명령어 '${subcommand}'`));
  printUsage();
  process.exit(1);
}
