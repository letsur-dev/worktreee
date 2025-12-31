import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from config import settings


class StateManager:
    def __init__(self):
        self.data_path = Path(settings.data_path)
        self.projects_file = self.data_path / "projects.yaml"
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        self.data_path.mkdir(parents=True, exist_ok=True)
        if not self.projects_file.exists():
            self._save({"projects": {}})

    def _load(self) -> dict:
        if not self.projects_file.exists():
            return {"projects": {}}
        with open(self.projects_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"projects": {}}

    def _save(self, data: dict):
        with open(self.projects_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def add_project(self, name: str, repo_path: str, machine: str = "local") -> dict:
        data = self._load()
        if name in data["projects"]:
            return {"error": f"프로젝트 '{name}'이(가) 이미 존재합니다."}

        data["projects"][name] = {
            "repo_path": repo_path,
            "machine": machine,
            "created": datetime.now().isoformat(),
            "tasks": {},
        }
        self._save(data)
        return {"success": True, "project": name}

    def list_projects(self) -> list[dict]:
        data = self._load()
        projects = []
        for name, info in data["projects"].items():
            projects.append({
                "name": name,
                "repo_path": info["repo_path"],
                "machine": info["machine"],
                "task_count": len(info.get("tasks", {})),
            })
        return projects

    def get_project(self, name: str) -> dict | None:
        data = self._load()
        return data["projects"].get(name)

    def add_task(
        self,
        project: str,
        task_name: str,
        context: str,
        branch: str | None = None,
        worktree: str | None = None,
    ) -> dict:
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'이(가) 이미 존재합니다."}

        branch = branch or task_name
        proj.setdefault("tasks", {})[task_name] = {
            "branch": branch,
            "worktree": worktree,
            "status": "pending",
            "context": context,
            "created": datetime.now().isoformat(),
            "reports": [],
        }
        self._save(data)
        return {"success": True, "project": project, "task": task_name}

    def update_task_status(self, project: str, task_name: str, status: str) -> dict:
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name not in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'을(를) 찾을 수 없습니다."}

        proj["tasks"][task_name]["status"] = status
        self._save(data)
        return {"success": True, "project": project, "task": task_name, "status": status}

    def add_report(self, project: str, task_name: str, content: str) -> dict:
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name not in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'을(를) 찾을 수 없습니다."}

        proj["tasks"][task_name]["reports"].append({
            "date": datetime.now().isoformat(),
            "content": content,
        })
        self._save(data)
        return {"success": True, "project": project, "task": task_name}

    def get_status(self, project: str | None = None) -> dict:
        data = self._load()

        if project:
            if project not in data["projects"]:
                return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}
            return data["projects"][project]

        # 전체 현황
        summary = {
            "total_projects": len(data["projects"]),
            "projects": [],
        }
        for name, info in data["projects"].items():
            tasks = info.get("tasks", {})
            task_summary = {
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
            }
            for task in tasks.values():
                status = task.get("status", "pending")
                if status in task_summary:
                    task_summary[status] += 1

            summary["projects"].append({
                "name": name,
                "machine": info["machine"],
                "tasks": task_summary,
            })
        return summary


# 싱글톤 인스턴스
state_manager = StateManager()
