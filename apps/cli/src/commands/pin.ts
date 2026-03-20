import { listProjects } from "../api";
import { bold, cyan, dim, green, red, yellow } from "../lib/colors";
import { select } from "../lib/prompt";
import { requestCd } from "../lib/cd";

export default async function pin(args: string[]) {
  const projects = await listProjects();

  const pinnedTasks = projects.flatMap((p) =>
    p.tasks
      .filter((t) => t.pinned && !t.archived_at)
      .map((t) => ({ ...t, projectName: p.name, projectTitle: p.title }))
  );

  if (pinnedTasks.length === 0) {
    console.log(dim("핀된 태스크가 없습니다."));
    return;
  }

  if (pinnedTasks.length === 1) {
    const task = pinnedTasks[0];
    if (!task.worktree) {
      console.error(yellow(`'${task.name}' 워크트리 없음`));
      return;
    }
    console.log(dim(`  ${task.projectTitle || task.projectName}/${task.name}`));
    requestCd(task.worktree);
    return;
  }

  const selected = await select({
    message: "📌 Pinned tasks",
    options: pinnedTasks.map((t) => ({
      label: t.name,
      value: t,
      hint: `${t.projectTitle || t.projectName} · ${t.branch}`,
    })),
  });

  if (!selected.worktree) {
    console.error(yellow(`'${selected.name}' 워크트리 없음`));
    return;
  }

  console.log(dim(`  ${selected.projectTitle || selected.projectName}/${selected.name}`));
  requestCd(selected.worktree);
}
