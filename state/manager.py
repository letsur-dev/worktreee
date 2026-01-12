import hashlib
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
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
            data = yaml.safe_load(f) or {}
            data.setdefault("projects", {})
            return data

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

    def list_projects(self, include_deleted: bool = False) -> list[dict]:
        data = self._load()
        projects = []
        for name, info in data["projects"].items():
            is_deleted = bool(info.get("deleted_at"))
            if is_deleted and not include_deleted:
                continue
            projects.append({
                "name": name,
                "repo_path": info["repo_path"],
                "machine": info["machine"],
                "task_count": len(info.get("tasks", {})),
                "deleted_at": info.get("deleted_at"),
            })
        return projects

    def get_project(self, name: str) -> dict | None:
        data = self._load()
        return data["projects"].get(name)

    def delete_project(self, name: str, hard: bool = False) -> dict:
        """프로젝트를 삭제합니다. (기본: soft delete)"""
        data = self._load()
        if name not in data["projects"]:
            return {"error": f"프로젝트 '{name}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][name]
        if proj.get("deleted_at") and not hard:
            return {"error": f"프로젝트 '{name}'은(는) 이미 삭제되었습니다."}

        if hard:
            del data["projects"][name]
            self._save(data)
            return {"success": True, "deleted": name, "type": "hard"}
        else:
            proj["deleted_at"] = datetime.now().isoformat()
            self._save(data)
            return {"success": True, "deleted": name, "type": "soft", "recoverable": True}

    def restore_project(self, name: str) -> dict:
        """삭제된 프로젝트를 복구합니다."""
        data = self._load()
        if name not in data["projects"]:
            return {"error": f"프로젝트 '{name}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][name]
        if not proj.get("deleted_at"):
            return {"error": f"프로젝트 '{name}'은(는) 삭제된 상태가 아닙니다."}

        del proj["deleted_at"]
        self._save(data)
        return {"success": True, "restored": name}

    def update_project(self, name: str, repo_path: str | None = None, machine: str | None = None) -> dict:
        """프로젝트 정보를 수정합니다."""
        data = self._load()
        if name not in data["projects"]:
            return {"error": f"프로젝트 '{name}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][name]
        updated = []
        if repo_path:
            proj["repo_path"] = repo_path
            updated.append("repo_path")
        if machine:
            proj["machine"] = machine
            updated.append("machine")

        if not updated:
            return {"error": "수정할 항목이 없습니다. repo_path 또는 machine을 지정해주세요."}

        self._save(data)
        return {"success": True, "project": name, "updated": updated}

    def add_task(
        self,
        project: str,
        task_name: str,
        context: str,
        branch: str | None = None,
        worktree: str | None = None,
        jira_key: str | None = None,
        notion_urls: list[str] | None = None,
    ) -> dict:
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'이(가) 이미 존재합니다."}

        branch = branch or task_name
        task_data = {
            "branch": branch,
            "worktree": worktree,
            "status": "pending",
            "context": context,
            "created": datetime.now().isoformat(),
        }

        # Jira 티켓 연결
        if jira_key:
            task_data["jira_key"] = jira_key

        # Notion 문서 연결
        if notion_urls:
            task_data["notion_urls"] = notion_urls

        proj.setdefault("tasks", {})[task_name] = task_data
        self._save(data)
        return {"success": True, "project": project, "task": task_name}

    def delete_task(self, project: str, task_name: str, cleanup_worktree: bool = True) -> dict:
        """태스크를 삭제합니다. 워크트리도 함께 정리할 수 있습니다."""
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name not in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'을(를) 찾을 수 없습니다."}

        task = proj["tasks"][task_name]
        worktree_path = task.get("worktree")
        machine = proj.get("machine", "local")

        # 워크트리 정리
        cleanup_result = None
        if cleanup_worktree and worktree_path:
            is_local = machine == "local" or machine.lower() == settings.local_machine.lower()
            if is_local:
                cleanup_result = self._cleanup_worktree_local(proj["repo_path"], worktree_path)
            else:
                resolved_host = self._resolve_host(machine)
                if not isinstance(resolved_host, dict):
                    cleanup_result = self._cleanup_worktree_remote(proj["repo_path"], worktree_path, resolved_host)

        # 태스크 삭제
        del proj["tasks"][task_name]
        self._save(data)

        return {
            "success": True,
            "project": project,
            "deleted_task": task_name,
            "worktree_cleanup": cleanup_result,
        }

    def _cleanup_worktree_local(self, repo_path: str, worktree_path: str) -> dict:
        """로컬 워크트리 정리"""
        try:
            # git worktree remove
            result = subprocess.run(
                ["git", "-C", repo_path, "worktree", "remove", worktree_path, "--force"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                return {"error": result.stderr}
            return {"success": True, "removed": worktree_path}
        except Exception as e:
            return {"error": str(e)}

    def _cleanup_worktree_remote(self, repo_path: str, worktree_path: str, host: str) -> dict:
        """원격 워크트리 정리"""
        repo_path = repo_path.replace("~", "$HOME")
        worktree_path = worktree_path.replace("~", "$HOME")

        script = f'''
cd {repo_path} || exit 1
git worktree remove "{worktree_path}" --force
'''
        cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", host, script]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return {"error": result.stderr or result.stdout}
            return {"success": True, "removed": worktree_path, "host": host}
        except Exception as e:
            return {"error": str(e)}

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

    def get_task_context(self, project: str, task_name: str) -> dict:
        """태스크의 전체 컨텍스트를 가져옵니다.
        연결된 Jira 이슈와 Notion 문서 내용을 함께 조회합니다.
        """
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name not in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'을(를) 찾을 수 없습니다."}

        task = proj["tasks"][task_name]
        result = {
            "project": project,
            "task_name": task_name,
            "branch": task.get("branch"),
            "worktree": task.get("worktree"),
            "status": task.get("status"),
            "context": task.get("context"),
            "created": task.get("created"),
        }

        # Jira 이슈 조회
        jira_key = task.get("jira_key")
        if jira_key:
            jira_result = self.get_jira_issue(jira_key, fetch_notion=True)
            if "error" not in jira_result:
                result["jira"] = jira_result

        # Notion 문서 조회
        notion_urls = task.get("notion_urls", [])
        if notion_urls:
            result["notion_pages"] = []
            for url in notion_urls:
                notion_result = self.get_notion_page(url)
                if "error" not in notion_result:
                    result["notion_pages"].append({
                        "url": url,
                        "content": notion_result.get("content", ""),
                    })

        return result

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
            if info.get("deleted_at"):
                continue  # 삭제된 프로젝트 제외

            tasks = info.get("tasks", {})
            task_summary = {
                "pending": 0,
                "in_progress": 0,
                "in_review": 0,
                "completed": 0,
            }
            tasks_with_pr = []
            for task_name, task in tasks.items():
                status = task.get("status", "pending")
                if status in task_summary:
                    task_summary[status] += 1

                # PR 정보가 있는 태스크 수집
                if task.get("pr"):
                    tasks_with_pr.append({
                        "name": task_name,
                        "pr": task["pr"],
                        "status": status,
                    })

            summary["projects"].append({
                "name": name,
                "machine": info["machine"],
                "tasks": task_summary,
                "tasks_with_pr": tasks_with_pr,
            })
        return summary

    def _resolve_host(self, host: str | None) -> str | None | dict:
        """호스트 별칭을 실제 SSH 주소로 변환. 에러시 dict 반환."""
        if not host:
            return None
        # @ 있으면 직접 SSH 주소로 간주
        if "@" in host:
            return host
        # 별칭에서 조회
        resolved = settings.remote_hosts_map.get(host.lower())
        if not resolved:
            available = list(settings.remote_hosts_map.keys())
            return {"error": f"알 수 없는 호스트 '{host}'. 사용 가능: {available or '(없음, REMOTE_HOSTS 설정 필요)'}"}
        return resolved

    def list_directory(self, path: str = "", host: str | None = None) -> dict:
        """디렉토리 내용을 조회합니다. Documents 하위만 접근 가능."""
        resolved_host = self._resolve_host(host)
        if isinstance(resolved_host, dict):  # 에러
            return resolved_host
        if resolved_host:
            base = settings.remote_base_path
            full_path = f"{base}/{path}".rstrip("/") if path else base
            return self._list_directory_remote(full_path, resolved_host)
        base = settings.local_base_path
        full_path = f"{base}/{path}".rstrip("/") if path else base
        return self._list_directory_local(full_path)

    def _list_directory_local(self, path: str) -> dict:
        """로컬 디렉토리 내용 조회 (폴더만)"""
        path = os.path.expanduser(path)

        if not os.path.isdir(path):
            return {"error": f"디렉토리가 존재하지 않습니다: {path}"}

        try:
            dirs = []
            for item in sorted(os.listdir(path)):
                if item.startswith("."):
                    continue
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    dirs.append(item)
            return {"path": path, "directories": dirs}
        except PermissionError:
            return {"error": f"권한이 없습니다: {path}"}

    def _list_directory_remote(self, path: str, host: str) -> dict:
        """SSH로 원격 디렉토리 내용 조회 (폴더만)"""
        path = path.replace("~", "$HOME")
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            host,
            f"ls -p {path} 2>/dev/null | grep '/$' | grep -v '^\\.' | sed 's|/$||'"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"error": f"SSH 연결 실패: {result.stderr}"}

            dirs = [d for d in result.stdout.strip().split("\n") if d]
            return {"host": host, "path": path, "directories": dirs}
        except subprocess.TimeoutExpired:
            return {"error": "SSH 연결 타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def scan_projects(self, path: str = "", host: str | None = None, max_depth: int = 3) -> dict:
        """디렉토리를 스캔하여 Git 레포를 찾습니다. Documents 하위만 접근 가능."""
        resolved_host = self._resolve_host(host)
        if isinstance(resolved_host, dict):  # 에러
            return resolved_host
        if resolved_host:
            base = settings.remote_base_path
            full_path = f"{base}/{path}".rstrip("/") if path else base
            return self._scan_projects_remote(full_path, resolved_host, max_depth)
        base = settings.local_base_path
        full_path = f"{base}/{path}".rstrip("/") if path else base
        return self._scan_projects_local(full_path, max_depth)

    def _scan_projects_local(self, path: str, max_depth: int = 3) -> dict:
        """로컬 디렉토리를 스캔하여 Git 레포 찾기 (재귀)"""
        path = os.path.expanduser(path)

        if not os.path.isdir(path):
            return {"error": f"디렉토리가 존재하지 않습니다: {path}"}

        data = self._load()
        registered_paths = {p["repo_path"] for p in data["projects"].values()}
        candidates = []

        def scan_recursive(dir_path: str, depth: int):
            if depth > max_depth:
                return
            try:
                for item in os.listdir(dir_path):
                    if item.startswith("."):
                        continue
                    item_path = os.path.join(dir_path, item)
                    if not os.path.isdir(item_path):
                        continue

                    git_path = os.path.join(item_path, ".git")
                    if os.path.exists(git_path):
                        candidates.append({
                            "name": item,
                            "path": item_path,
                            "registered": item_path in registered_paths,
                        })
                    else:
                        scan_recursive(item_path, depth + 1)
            except PermissionError:
                pass

        scan_recursive(path, 0)

        return {
            "scan_path": path,
            "total": len(candidates),
            "registered": sum(1 for c in candidates if c["registered"]),
            "unregistered": sum(1 for c in candidates if not c["registered"]),
            "candidates": candidates,
        }

    def _scan_projects_remote(self, path: str, host: str, max_depth: int = 3) -> dict:
        """SSH로 원격 디렉토리를 스캔하여 Git 레포 찾기"""
        path = path.replace("~", "$HOME")

        # find 명령으로 .git 디렉토리 찾기
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            host,
            f"find {path} -maxdepth {max_depth + 1} -name .git -type d 2>/dev/null"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"error": f"SSH 연결 실패: {result.stderr}"}

            git_dirs = result.stdout.strip().split("\n")
            git_dirs = [d for d in git_dirs if d]  # 빈 줄 제거

            data = self._load()
            registered_paths = {p["repo_path"] for p in data["projects"].values()}

            candidates = []
            for git_dir in git_dirs:
                repo_path = git_dir.rsplit("/.git", 1)[0]
                name = os.path.basename(repo_path)
                candidates.append({
                    "name": name,
                    "path": repo_path,
                    "host": host,
                    "registered": repo_path in registered_paths,
                })

            return {
                "host": host,
                "scan_path": path,
                "total": len(candidates),
                "registered": sum(1 for c in candidates if c["registered"]),
                "unregistered": sum(1 for c in candidates if not c["registered"]),
                "candidates": candidates,
            }
        except subprocess.TimeoutExpired:
            return {"error": "SSH 연결 타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def _sanitize_branch_name(self, branch: str) -> str:
        """브랜치 이름을 디렉토리명으로 변환 (flat 구조)"""
        # feature/PROJ-123/auth -> feature-PROJ-123-auth
        return branch.replace("/", "-").replace("\\", "-")

    def create_worktree(self, project: str, task_name: str) -> dict:
        """태스크용 Git worktree를 생성합니다."""
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name not in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'을(를) 찾을 수 없습니다."}

        task = proj["tasks"][task_name]
        if task.get("worktree"):
            return {"error": f"워크트리가 이미 존재합니다: {task['worktree']}"}

        repo_path = proj["repo_path"]
        machine = proj.get("machine", "local")
        branch = task.get("branch", task_name)
        # 워크트리 폴더명: task_name 사용 (사용자가 지정한 그대로)
        # 브랜치명: branch 필드 사용 (feature/PROJ-123/xxx 형태 가능)
        folder_name = self._sanitize_branch_name(task_name)  # task_name 기반 폴더명
        # 짧은 해시 생성 (타임스탬프 기반, 7자)
        short_hash = hashlib.sha1(str(time.time()).encode()).hexdigest()[:7]
        # 워크트리 폴더 구조: {repo}-worktrees/{task_name}-{hash}
        worktrees_dir = f"{repo_path}-worktrees"
        worktree_path = f"{worktrees_dir}/{folder_name}-{short_hash}"

        # 머신에 따라 로컬/원격 실행
        # "local" 또는 local_machine 설정값(기본: "nuc")이면 로컬 실행
        is_local = machine == "local" or machine.lower() == settings.local_machine.lower()
        if is_local:
            result = self._create_worktree_local(repo_path, worktree_path, branch)
        else:
            # machine이 호스트 별칭이거나 직접 주소
            resolved_host = self._resolve_host(machine)
            if isinstance(resolved_host, dict):  # 에러
                return resolved_host
            result = self._create_worktree_remote(repo_path, worktree_path, branch, resolved_host)

        if "error" in result:
            return result

        # 성공시 태스크에 worktree 경로 저장
        task["worktree"] = worktree_path
        self._save(data)
        return {
            "success": True,
            "project": project,
            "task": task_name,
            "worktree": worktree_path,
            "branch": branch,
        }

    def _create_worktree_local(self, repo_path: str, worktree_path: str, branch: str) -> dict:
        """로컬에서 Git worktree 생성"""
        try:
            # 이미 워크트리가 있는지 확인
            if os.path.exists(worktree_path):
                return {"error": f"디렉토리가 이미 존재합니다: {worktree_path}"}

            # worktrees 디렉토리 생성
            worktrees_dir = os.path.dirname(worktree_path)
            os.makedirs(worktrees_dir, exist_ok=True)

            # 최신 원격 브랜치 정보 가져오기
            subprocess.run(
                ["git", "-C", repo_path, "fetch", "origin"],
                capture_output=True, text=True, timeout=60
            )

            # 브랜치 존재 여부 확인
            check_branch = subprocess.run(
                ["git", "-C", repo_path, "rev-parse", "--verify", branch],
                capture_output=True, text=True
            )
            branch_exists = check_branch.returncode == 0

            # 원격 브랜치 확인
            if not branch_exists:
                check_remote = subprocess.run(
                    ["git", "-C", repo_path, "rev-parse", "--verify", f"origin/{branch}"],
                    capture_output=True, text=True
                )
                if check_remote.returncode == 0:
                    branch_exists = True

            # 워크트리 생성
            if branch_exists:
                # 기존 브랜치로 워크트리 생성
                cmd = ["git", "-C", repo_path, "worktree", "add", worktree_path, branch]
            else:
                # 새 브랜치 생성하며 워크트리 생성
                cmd = ["git", "-C", repo_path, "worktree", "add", "-b", branch, worktree_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return {"error": f"워크트리 생성 실패: {result.stderr}"}

            return {"success": True, "worktree": worktree_path}
        except subprocess.TimeoutExpired:
            return {"error": "워크트리 생성 타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def _create_worktree_remote(self, repo_path: str, worktree_path: str, branch: str, host: str) -> dict:
        """SSH로 원격에서 Git worktree 생성"""
        # 원격 경로에서 ~ 처리
        repo_path = repo_path.replace("~", "$HOME")
        worktree_path = worktree_path.replace("~", "$HOME")

        # worktrees 디렉토리 경로
        worktrees_dir = os.path.dirname(worktree_path)

        # 브랜치 존재 여부 확인 후 워크트리 생성하는 스크립트
        script = f'''
cd {repo_path} || exit 1
if [ -d "{worktree_path}" ]; then
    echo "ERROR: 디렉토리가 이미 존재합니다: {worktree_path}"
    exit 1
fi
# worktrees 디렉토리 생성
mkdir -p "{worktrees_dir}"
# 최신 원격 브랜치 정보 가져오기
git fetch origin
# 브랜치 존재 여부 확인
if git rev-parse --verify {branch} >/dev/null 2>&1 || git rev-parse --verify origin/{branch} >/dev/null 2>&1; then
    git worktree add "{worktree_path}" {branch}
else
    git worktree add -b {branch} "{worktree_path}"
fi
'''
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            host, script
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                return {"error": f"워크트리 생성 실패: {error_msg}"}

            return {"success": True, "worktree": worktree_path, "host": host}
        except subprocess.TimeoutExpired:
            return {"error": "SSH 연결 타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def sync_worktree(self, project: str, task_name: str, base_branch: str = "develop") -> dict:
        """워크트리 브랜치를 base_branch 기준으로 rebase합니다."""
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name not in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'을(를) 찾을 수 없습니다."}

        task = proj["tasks"][task_name]
        worktree_path = task.get("worktree")
        if not worktree_path:
            return {"error": f"워크트리가 없습니다. 먼저 create_worktree를 실행해주세요."}

        machine = proj.get("machine", "local")
        repo_path = proj["repo_path"]

        # 머신에 따라 로컬/원격 실행
        is_local = machine == "local" or machine.lower() == settings.local_machine.lower()
        if is_local:
            result = self._sync_worktree_local(repo_path, worktree_path, base_branch)
        else:
            resolved_host = self._resolve_host(machine)
            if isinstance(resolved_host, dict):
                return resolved_host
            result = self._sync_worktree_remote(repo_path, worktree_path, base_branch, resolved_host)

        return result

    def _sync_worktree_local(self, repo_path: str, worktree_path: str, base_branch: str) -> dict:
        """로컬 워크트리 rebase"""
        try:
            # 1. 메인 레포에서 fetch
            fetch_result = subprocess.run(
                ["git", "-C", repo_path, "fetch", "origin"],
                capture_output=True, text=True, timeout=60
            )
            if fetch_result.returncode != 0:
                return {"error": f"fetch 실패: {fetch_result.stderr}"}

            # 2. 워크트리에서 rebase
            rebase_result = subprocess.run(
                ["git", "-C", worktree_path, "rebase", f"origin/{base_branch}"],
                capture_output=True, text=True, timeout=120
            )
            if rebase_result.returncode != 0:
                # rebase 충돌 발생
                subprocess.run(
                    ["git", "-C", worktree_path, "rebase", "--abort"],
                    capture_output=True, text=True
                )
                return {
                    "error": "rebase 충돌 발생. 수동 해결 필요.",
                    "conflict": True,
                    "message": rebase_result.stderr
                }

            return {
                "success": True,
                "worktree": worktree_path,
                "rebased_onto": f"origin/{base_branch}",
                "message": rebase_result.stdout or "Rebase 완료"
            }
        except subprocess.TimeoutExpired:
            return {"error": "타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def _sync_worktree_remote(self, repo_path: str, worktree_path: str, base_branch: str, host: str) -> dict:
        """원격 워크트리 rebase"""
        repo_path = repo_path.replace("~", "$HOME")
        worktree_path = worktree_path.replace("~", "$HOME")

        script = f'''
cd {repo_path} || exit 1
git fetch origin
cd {worktree_path} || exit 1
if ! git rebase origin/{base_branch}; then
    git rebase --abort
    echo "CONFLICT: rebase 충돌 발생. 수동 해결 필요."
    exit 1
fi
echo "Rebase 완료: origin/{base_branch}"
'''
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            host, script
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                if "CONFLICT" in error_msg or "conflict" in error_msg.lower():
                    return {"error": "rebase 충돌 발생. 수동 해결 필요.", "conflict": True}
                return {"error": f"rebase 실패: {error_msg}"}

            return {
                "success": True,
                "worktree": worktree_path,
                "rebased_onto": f"origin/{base_branch}",
                "host": host
            }
        except subprocess.TimeoutExpired:
            return {"error": "SSH 연결 타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def start_claude_session(self, project: str, task_name: str) -> dict:
        """태스크용 Claude Code 세션을 시작하고 레포 분석을 수행합니다."""
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if task_name not in proj.get("tasks", {}):
            return {"error": f"태스크 '{task_name}'을(를) 찾을 수 없습니다."}

        task = proj["tasks"][task_name]
        worktree_path = task.get("worktree")
        if not worktree_path:
            return {"error": "워크트리가 없습니다. 먼저 create_worktree를 실행해주세요."}

        context = task.get("context", "")
        branch = task.get("branch", task_name)

        # Claude에게 전달할 프롬프트
        prompt = f"""이 레포지토리를 분석하고 다음 태스크를 이해해주세요.

## 태스크 정보
- 프로젝트: {project}
- 브랜치: {branch}
- 워크트리: {worktree_path}

## 태스크 컨텍스트
{context}

## 요청사항
1. 레포지토리 구조를 파악해주세요
2. 태스크 수행에 필요한 파일들을 찾아주세요
3. 구현 계획을 간단히 세워주세요

분석이 완료되면 사용자가 'claude --continue'로 이어서 작업할 수 있습니다."""

        machine = proj.get("machine", "local")
        is_local = machine == "local" or machine.lower() == settings.local_machine.lower()

        if is_local:
            result = self._start_claude_session_local(worktree_path, prompt)
        else:
            resolved_host = self._resolve_host(machine)
            if isinstance(resolved_host, dict):
                return resolved_host
            result = self._start_claude_session_remote(worktree_path, prompt, resolved_host)

        # 세션 정보 저장
        if result.get("success"):
            task["claude_session"] = {
                "started": datetime.now().isoformat(),
                "worktree": worktree_path,
            }
            self._save(data)

        return result

    def _start_claude_session_local(self, worktree_path: str, prompt: str) -> dict:
        """로컬에서 Claude 세션 시작"""
        try:
            # claude -p "prompt" --print 로 실행 (non-interactive)
            result = subprocess.run(
                ["claude", "-p", prompt, "--print"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )

            if result.returncode != 0:
                return {"error": f"Claude 실행 실패: {result.stderr}"}

            # Docker에서 실행시 세션 폴더 권한 수정 (호스트 유저가 접근 가능하도록)
            session_dir = Path("/root/.claude/projects")
            if session_dir.exists():
                # 워크트리 경로로 세션 폴더명 추측 (Claude는 앞에 - 붙임)
                sanitized = worktree_path.replace("/", "-")
                session_path = session_dir / sanitized
                if session_path.exists():
                    subprocess.run(["chmod", "-R", "777", str(session_path)], capture_output=True)

            return {
                "success": True,
                "worktree": worktree_path,
                "analysis": result.stdout,
                "message": f"세션 시작 완료. 'cd {worktree_path} && claude --continue'로 이어서 작업하세요."
            }
        except subprocess.TimeoutExpired:
            return {"error": "Claude 세션 타임아웃 (5분)"}
        except FileNotFoundError:
            return {"error": "Claude CLI가 설치되어 있지 않습니다."}
        except Exception as e:
            return {"error": str(e)}

    def _start_claude_session_remote(self, worktree_path: str, prompt: str, host: str) -> dict:
        """원격에서 Claude 세션 시작"""
        worktree_path = worktree_path.replace("~", "$HOME")
        # 프롬프트에서 특수문자 이스케이프
        escaped_prompt = prompt.replace("'", "'\\''")

        # SSH non-interactive shell에서 PATH 문제 해결
        # .zshrc 또는 .bashrc를 source해서 nvm/PATH 설정 로드
        script = f'''
# 쉘 환경 로드 (zsh 또는 bash)
if [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc" 2>/dev/null
elif [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc" 2>/dev/null
fi

cd {worktree_path} || exit 1
claude -p '{escaped_prompt}' --print
'''
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            host, script
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return {"error": f"Claude 실행 실패: {result.stderr or result.stdout}"}

            return {
                "success": True,
                "worktree": worktree_path,
                "host": host,
                "analysis": result.stdout,
                "message": f"세션 시작 완료. 원격에서 'cd {worktree_path} && claude --continue'로 이어서 작업하세요."
            }
        except subprocess.TimeoutExpired:
            return {"error": "SSH/Claude 세션 타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def _extract_notion_urls(self, text: str | None) -> list[str]:
        """텍스트에서 Notion URL 추출"""
        import re
        if not text:
            return []
        # notion.so 또는 notion.site URL 패턴
        pattern = r'https?://(?:www\.)?notion\.(?:so|site)/[^\s\)\]\>\"\'<]+'
        urls = re.findall(pattern, text)
        # 중복 제거
        return list(dict.fromkeys(urls))

    def get_jira_issue(self, issue_key: str, include_children: bool = True, recursive: bool = False, fetch_notion: bool = True) -> dict:
        """Jira 이슈 정보를 조회합니다.

        Args:
            issue_key: Jira 이슈 키 (예: PRDEL-85)
            include_children: 직접 하위 이슈 포함 여부
            recursive: True면 하위의 하위, 링크된 이슈까지 재귀적으로 전체 트리 조회
            fetch_notion: True면 Notion 링크 발견시 자동으로 내용 조회
        """
        import requests
        from requests.auth import HTTPBasicAuth

        if not settings.jira_url or not settings.jira_email or not settings.jira_api_token:
            return {"error": "Jira API 설정이 없습니다. JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN을 설정해주세요."}

        auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
        headers = {"Accept": "application/json"}

        if recursive:
            return self._get_jira_issue_tree(issue_key, auth, headers, visited=set(), max_depth=5)

        try:
            # 메인 이슈 조회 (댓글, 첨부파일 포함)
            url = f"{settings.jira_url}/rest/api/3/issue/{issue_key}?fields=*all,-worklog&expand=renderedFields,comment"
            response = requests.get(url, headers=headers, auth=auth, timeout=30)
            if response.status_code == 404:
                return {"error": f"이슈 '{issue_key}'를 찾을 수 없습니다."}
            if response.status_code != 200:
                return {"error": f"Jira API 오류: {response.status_code} - {response.text}"}

            data = response.json()
            fields = data.get("fields", {})
            issue_type = fields.get("issuetype", {}).get("name") if fields.get("issuetype") else None

            # 기본 정보 추출
            result = {
                "key": data.get("key"),
                "summary": fields.get("summary"),
                "description": self._extract_jira_description(fields.get("description")),
                "status": fields.get("status", {}).get("name"),
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
                "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                "issue_type": issue_type,
                "project": fields.get("project", {}).get("name") if fields.get("project") else None,
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "url": f"{settings.jira_url}/browse/{issue_key}",
            }

            # 댓글 추가
            comments_data = fields.get("comment", {}).get("comments", [])
            if comments_data:
                result["comments"] = []
                for c in comments_data:
                    comment_text = self._extract_jira_description(c.get("body"))
                    result["comments"].append({
                        "author": c.get("author", {}).get("displayName"),
                        "created": c.get("created", "")[:10],
                        "body": comment_text,
                    })

            # 첨부파일 추가
            attachments = fields.get("attachment", [])
            if attachments:
                result["attachments"] = []
                for a in attachments:
                    result["attachments"].append({
                        "filename": a.get("filename"),
                        "mimeType": a.get("mimeType"),
                        "size": a.get("size"),
                        "url": a.get("content"),  # 다운로드 URL
                    })

            if not include_children:
                return result

            # Subtasks 조회
            subtasks = fields.get("subtasks", [])
            if subtasks:
                result["subtasks"] = [
                    {
                        "key": st.get("key"),
                        "summary": st.get("fields", {}).get("summary"),
                        "status": st.get("fields", {}).get("status", {}).get("name"),
                        "issue_type": st.get("fields", {}).get("issuetype", {}).get("name"),
                    }
                    for st in subtasks
                ]

            # Linked Issues 조회
            issuelinks = fields.get("issuelinks", [])
            if issuelinks:
                linked = []
                for link in issuelinks:
                    link_type = link.get("type", {}).get("name", "관련")
                    if "outwardIssue" in link:
                        issue = link["outwardIssue"]
                        direction = link.get("type", {}).get("outward", "links to")
                    elif "inwardIssue" in link:
                        issue = link["inwardIssue"]
                        direction = link.get("type", {}).get("inward", "linked from")
                    else:
                        continue
                    linked.append({
                        "key": issue.get("key"),
                        "summary": issue.get("fields", {}).get("summary"),
                        "status": issue.get("fields", {}).get("status", {}).get("name"),
                        "link_type": f"{link_type} ({direction})",
                    })
                if linked:
                    result["linked_issues"] = linked

            # 하위 이슈 조회 (JQL 검색) - subtasks가 없는 경우
            # Epic, Project, Scope 등 상위 타입은 parent 관계로 하위 이슈를 가질 수 있음
            if not subtasks:
                children = self._get_children(issue_key, auth, headers)
                if children:
                    result["children"] = children

            # Parent 정보 (이 이슈가 하위 이슈인 경우)
            parent = fields.get("parent")
            if parent:
                result["parent"] = {
                    "key": parent.get("key"),
                    "summary": parent.get("fields", {}).get("summary"),
                    "status": parent.get("fields", {}).get("status", {}).get("name"),
                    "issue_type": parent.get("fields", {}).get("issuetype", {}).get("name"),
                }

            # Notion 링크 자동 조회
            if fetch_notion:
                notion_urls = set()
                # description에서 추출
                notion_urls.update(self._extract_notion_urls(result.get("description")))
                # 댓글에서 추출
                for comment in result.get("comments", []):
                    notion_urls.update(self._extract_notion_urls(comment.get("body")))

                if notion_urls:
                    result["notion_pages"] = []
                    for url in list(notion_urls)[:5]:  # 최대 5개
                        notion_result = self.get_notion_page(url)
                        if "error" not in notion_result:
                            result["notion_pages"].append({
                                "url": url,
                                "content": notion_result.get("content", "")[:2000],  # 내용 2000자 제한
                            })

            return result
        except requests.exceptions.Timeout:
            return {"error": "Jira API 타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def _get_children(self, issue_key: str, auth, headers) -> list:
        """parent 관계의 하위 이슈들을 JQL로 조회"""
        import requests

        # parent 필드 또는 Epic Link로 연결된 이슈 검색
        jql = f'parent = {issue_key} OR "Epic Link" = {issue_key}'
        url = f"{settings.jira_url}/rest/api/3/search/jql"
        req_headers = {**headers, "Content-Type": "application/json"}
        body = {
            "jql": jql,
            "fields": ["key", "summary", "status", "issuetype", "assignee"],
            "maxResults": 50,
        }

        try:
            response = requests.post(url, headers=req_headers, auth=auth, json=body, timeout=30)
            if response.status_code != 200:
                return []

            data = response.json()
            children = []
            for issue in data.get("issues", []):
                fields = issue.get("fields", {})
                children.append({
                    "key": issue.get("key"),
                    "summary": fields.get("summary"),
                    "status": fields.get("status", {}).get("name"),
                    "issue_type": fields.get("issuetype", {}).get("name"),
                    "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                })
            return children
        except Exception:
            return []

    def _get_jira_issue_tree(self, issue_key: str, auth, headers, visited: set, max_depth: int, depth: int = 0) -> dict:
        """재귀적으로 이슈 트리 전체를 조회 (하위의 하위, 링크된 이슈 포함)"""
        import requests

        # 무한 루프 방지
        if issue_key in visited or depth > max_depth:
            return {"key": issue_key, "_skipped": True, "_reason": "already visited" if issue_key in visited else "max depth"}

        visited.add(issue_key)

        # 이슈 조회
        url = f"{settings.jira_url}/rest/api/3/issue/{issue_key}"
        try:
            response = requests.get(url, headers=headers, auth=auth, timeout=30)
            if response.status_code != 200:
                return {"key": issue_key, "_error": f"HTTP {response.status_code}"}

            data = response.json()
            fields = data.get("fields", {})

            result = {
                "key": data.get("key"),
                "summary": fields.get("summary"),
                "status": fields.get("status", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name") if fields.get("issuetype") else None,
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
            }

            # Subtasks 재귀 조회
            subtasks = fields.get("subtasks", [])
            if subtasks:
                result["subtasks"] = []
                for st in subtasks:
                    st_key = st.get("key")
                    if st_key and st_key not in visited:
                        child_result = self._get_jira_issue_tree(st_key, auth, headers, visited, max_depth, depth + 1)
                        result["subtasks"].append(child_result)

            # Children 재귀 조회 (parent 관계)
            if not subtasks:
                children_keys = self._get_children(issue_key, auth, headers)
                if children_keys:
                    result["children"] = []
                    for child in children_keys:
                        child_key = child.get("key")
                        if child_key and child_key not in visited:
                            child_result = self._get_jira_issue_tree(child_key, auth, headers, visited, max_depth, depth + 1)
                            result["children"].append(child_result)

            # Linked Issues 재귀 조회
            issuelinks = fields.get("issuelinks", [])
            if issuelinks:
                result["linked_issues"] = []
                for link in issuelinks:
                    link_type = link.get("type", {}).get("name", "관련")
                    if "outwardIssue" in link:
                        issue = link["outwardIssue"]
                        direction = link.get("type", {}).get("outward", "links to")
                    elif "inwardIssue" in link:
                        issue = link["inwardIssue"]
                        direction = link.get("type", {}).get("inward", "linked from")
                    else:
                        continue

                    linked_key = issue.get("key")
                    if linked_key and linked_key not in visited:
                        linked_result = self._get_jira_issue_tree(linked_key, auth, headers, visited, max_depth, depth + 1)
                        linked_result["_link_type"] = f"{link_type} ({direction})"
                        result["linked_issues"].append(linked_result)

                if not result["linked_issues"]:
                    del result["linked_issues"]

            return result
        except Exception as e:
            return {"key": issue_key, "_error": str(e)}

    def _tree_to_mermaid(self, tree: dict) -> str:
        """이슈 트리를 Mermaid 다이어그램으로 변환"""
        lines = ["graph TD"]
        edges = []
        visited = set()

        def status_emoji(status: str | None) -> str:
            if not status:
                return "⚪"
            s = status.lower()
            if "progress" in s:
                return "🟡"
            if "done" in s or "complete" in s or "merged" in s or "deployed" in s:
                return "🟢"
            if "review" in s:
                return "🔵"
            return "⚪"

        def escape_label(text: str) -> str:
            # Mermaid에서 특수문자 이스케이프
            return text.replace('"', "'").replace("[", "(").replace("]", ")")[:40]

        def process_node(node: dict, parent_key: str | None = None, link_type: str | None = None):
            if not node or node.get("_skipped") or node.get("_error"):
                return

            key = node.get("key")
            if not key or key in visited:
                return
            visited.add(key)

            # 노드 정의
            emoji = status_emoji(node.get("status"))
            summary = escape_label(node.get("summary") or "")
            lines.append(f'    {key}["{emoji} {key}: {summary}"]')

            # 엣지 (부모 → 자식)
            if parent_key:
                if link_type:
                    edges.append(f'    {parent_key} -.->|"{link_type}"| {key}')
                else:
                    edges.append(f"    {parent_key} --> {key}")

            # 하위 이슈 처리
            for child in node.get("children", []):
                process_node(child, key)
            for child in node.get("subtasks", []):
                process_node(child, key)

            # 링크된 이슈 처리 (점선)
            for linked in node.get("linked_issues", []):
                lt = linked.get("_link_type", "related")
                # 짧게 줄이기
                if "blocks" in lt.lower():
                    lt = "blocks"
                elif "relates" in lt.lower():
                    lt = "relates"
                process_node(linked, key, lt)

        process_node(tree)
        return "\n".join(lines + edges)

    def get_jira_graph(self, issue_key: str) -> dict:
        """Jira 이슈 트리를 Mermaid 그래프로 반환"""
        import requests
        from requests.auth import HTTPBasicAuth

        if not settings.jira_url or not settings.jira_email or not settings.jira_api_token:
            return {"error": "Jira API 설정이 없습니다."}

        auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
        headers = {"Accept": "application/json"}

        tree = self._get_jira_issue_tree(issue_key, auth, headers, visited=set(), max_depth=5)
        if "error" in tree or "_error" in tree:
            return tree

        mermaid = self._tree_to_mermaid(tree)
        return {
            "issue_key": issue_key,
            "mermaid": mermaid,
            "node_count": mermaid.count('["'),
        }

    def _tree_to_graph_data(self, tree: dict) -> dict:
        """이슈 트리를 D3 그래프용 nodes/links 데이터로 변환"""
        nodes = []
        links = []
        visited = set()

        def get_status_color(status: str | None) -> str:
            """상태별 테두리 색상"""
            if not status:
                return "#9ca3af"  # gray
            s = status.lower()
            if "progress" in s:
                return "#eab308"  # yellow
            if "done" in s or "complete" in s or "merged" in s or "deployed" in s:
                return "#22c55e"  # green
            if "review" in s:
                return "#3b82f6"  # blue
            return "#9ca3af"  # gray

        def get_type_info(issue_type: str | None) -> tuple[str, int]:
            """이슈 타입별 배경색과 크기"""
            if not issue_type:
                return "#475569", 25  # default gray, medium
            t = issue_type.lower()
            if "epic" in t:
                return "#7c3aed", 40  # purple, large
            if "story" in t or "feature" in t:
                return "#2563eb", 32  # blue, medium-large
            if "bug" in t:
                return "#dc2626", 28  # red, medium
            if "task" in t:
                return "#0891b2", 25  # cyan, medium
            if "subtask" in t or "sub-task" in t:
                return "#64748b", 20  # gray, small
            return "#475569", 25  # default

        def process_node(node: dict, parent_key: str | None = None, link_type: str | None = None, depth: int = 0):
            if not node or node.get("_skipped") or node.get("_error"):
                return

            key = node.get("key")
            if not key:
                return

            # 노드가 처음이면 추가
            if key not in visited:
                visited.add(key)
                issue_type = node.get("issue_type", "")
                bg_color, _ = get_type_info(issue_type)
                # 계층별 크기: depth 0 = 45, depth 1 = 35, depth 2 = 28, depth 3+ = 22
                size = max(22, 45 - (depth * 10))
                nodes.append({
                    "id": key,
                    "label": node.get("summary", "")[:50],
                    "status": node.get("status", ""),
                    "type": issue_type,
                    "bgColor": bg_color,
                    "strokeColor": get_status_color(node.get("status")),
                    "size": size,
                    "depth": depth,
                })

            # 엣지 추가 (부모 → 자식)
            if parent_key:
                link_id = f"{parent_key}->{key}"
                reverse_link_id = f"{key}->{parent_key}"
                # 중복 방지
                existing_links = {f"{l['source']}->{l['target']}" for l in links}
                if link_id not in existing_links and reverse_link_id not in existing_links:
                    links.append({
                        "source": parent_key,
                        "target": key,
                        "type": link_type or "child",
                        "dashed": link_type is not None,
                    })

            # 하위 이슈 처리 (depth 증가)
            for child in node.get("children", []):
                process_node(child, key, None, depth + 1)
            for child in node.get("subtasks", []):
                process_node(child, key, None, depth + 1)

            # 링크된 이슈 처리 (같은 depth - 관계이므로)
            for linked in node.get("linked_issues", []):
                lt = linked.get("_link_type", "related")
                if "blocks" in lt.lower():
                    lt = "blocks"
                elif "relates" in lt.lower():
                    lt = "relates"
                elif "duplicate" in lt.lower():
                    lt = "duplicate"
                process_node(linked, key, lt, depth)

        process_node(tree)
        return {"nodes": nodes, "links": links}

    def get_jira_graph_html(self, issue_key: str, output_path: str | None = None) -> dict:
        """Jira 이슈 그래프를 D3.js 인터랙티브 HTML로 생성"""
        import requests
        from requests.auth import HTTPBasicAuth
        import json as json_module

        if not settings.jira_url or not settings.jira_email or not settings.jira_api_token:
            return {"error": "Jira API 설정이 없습니다."}

        auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
        headers = {"Accept": "application/json"}

        tree = self._get_jira_issue_tree(issue_key, auth, headers, visited=set(), max_depth=5)
        if "error" in tree or "_error" in tree:
            return tree

        graph_data = self._tree_to_graph_data(tree)
        jira_base_url = settings.jira_url

        html_template = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jira Issue Graph - {issue_key}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            overflow: hidden;
        }}
        #graph {{ width: 100vw; height: 100vh; }}
        .node {{ cursor: pointer; }}
        .node text {{ font-size: 10px; fill: #fff; font-weight: 500; }}
        .link {{ fill: none; stroke-opacity: 0.7; }}
        .link.child {{ stroke: #64748b; stroke-width: 2px; }}
        .link.dashed {{ stroke-dasharray: 5, 5; stroke: #a855f7; stroke-width: 2px; }}
        .link-label {{ font-size: 9px; fill: #c084fc; font-weight: 500; }}
        .tooltip {{
            position: absolute;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            max-width: 300px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            z-index: 1000;
        }}
        .tooltip .key {{ color: #60a5fa; font-weight: bold; font-size: 14px; }}
        .tooltip .summary {{ margin-top: 4px; color: #e2e8f0; }}
        .tooltip .meta {{ margin-top: 8px; color: #94a3b8; font-size: 11px; }}
        .legend {{
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 16px;
            font-size: 12px;
        }}
        .legend h4 {{ margin: 0 0 8px 0; color: #94a3b8; font-size: 10px; text-transform: uppercase; }}
        .legend-item {{ display: flex; align-items: center; margin: 4px 0; }}
        .legend-color {{ width: 14px; height: 14px; border-radius: 50%; margin-right: 8px; border: 2px solid transparent; }}
        .legend-line {{ width: 24px; margin-right: 8px; }}
        .controls {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
        }}
        .controls button {{
            background: #334155;
            border: none;
            color: #e2e8f0;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 2px;
        }}
        .controls button:hover {{ background: #475569; }}
    </style>
</head>
<body>
    <div id="graph"></div>
    <div class="tooltip" id="tooltip"></div>
    <div class="legend">
        <h4>Issue Type</h4>
        <div class="legend-item"><div class="legend-color" style="background:#7c3aed; width:20px; height:20px;"></div>Epic</div>
        <div class="legend-item"><div class="legend-color" style="background:#2563eb; width:16px; height:16px;"></div>Story</div>
        <div class="legend-item"><div class="legend-color" style="background:#0891b2; width:14px; height:14px;"></div>Task</div>
        <div class="legend-item"><div class="legend-color" style="background:#dc2626; width:14px; height:14px;"></div>Bug</div>
        <div class="legend-item"><div class="legend-color" style="background:#64748b; width:12px; height:12px;"></div>Subtask</div>
        <h4 style="margin-top: 12px;">Status (Border)</h4>
        <div class="legend-item"><div class="legend-color" style="background:#334155; border-color:#22c55e;"></div>Done</div>
        <div class="legend-item"><div class="legend-color" style="background:#334155; border-color:#3b82f6;"></div>In Review</div>
        <div class="legend-item"><div class="legend-color" style="background:#334155; border-color:#eab308;"></div>In Progress</div>
        <div class="legend-item"><div class="legend-color" style="background:#334155; border-color:#9ca3af;"></div>To Do</div>
        <h4 style="margin-top: 12px;">Links</h4>
        <div class="legend-item"><svg class="legend-line" height="10"><line x1="0" y1="5" x2="24" y2="5" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/></svg>Parent → Child</div>
        <div class="legend-item"><svg class="legend-line" height="10"><line x1="0" y1="5" x2="24" y2="5" stroke="#a855f7" stroke-width="2" stroke-dasharray="3,3"/></svg>Issue Link</div>
    </div>
    <div class="controls">
        <button onclick="zoomIn()">+ Zoom In</button>
        <button onclick="zoomOut()">- Zoom Out</button>
        <button onclick="resetZoom()">Reset</button>
    </div>
    <script>
        const data = {json_module.dumps(graph_data)};
        const jiraUrl = "{jira_base_url}";

        const width = window.innerWidth;
        const height = window.innerHeight;

        const svg = d3.select("#graph")
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        // Arrow marker 정의
        svg.append("defs").selectAll("marker")
            .data(["arrow", "arrow-link"])
            .join("marker")
            .attr("id", d => d)
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", d => d === "arrow" ? 20 : 15)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("fill", d => d === "arrow" ? "#64748b" : "#a855f7")
            .attr("d", "M0,-5L10,0L0,5");

        const g = svg.append("g");

        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => g.attr("transform", event.transform));

        svg.call(zoom);

        window.zoomIn = () => svg.transition().call(zoom.scaleBy, 1.3);
        window.zoomOut = () => svg.transition().call(zoom.scaleBy, 0.7);
        window.resetZoom = () => svg.transition().call(zoom.transform, d3.zoomIdentity);

        // Free force layout
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(150))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => d.size + 30));

        // Links
        const link = g.append("g")
            .selectAll("line")
            .data(data.links)
            .join("line")
            .attr("class", d => "link " + (d.dashed ? "dashed" : "child"))
            .attr("marker-end", d => d.dashed ? "url(#arrow-link)" : "url(#arrow)");

        // Link labels
        const linkLabel = g.append("g")
            .selectAll("text")
            .data(data.links.filter(d => d.dashed))
            .join("text")
            .attr("class", "link-label")
            .text(d => d.type);

        // Nodes
        const node = g.append("g")
            .selectAll(".node")
            .data(data.nodes)
            .join("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

        node.append("circle")
            .attr("r", d => d.size)
            .attr("fill", d => d.bgColor)
            .attr("stroke", d => d.strokeColor)
            .attr("stroke-width", 3);

        // 이슈 키 (노드 안)
        node.append("text")
            .attr("dy", -2)
            .attr("text-anchor", "middle")
            .attr("class", "node-key")
            .style("font-size", d => Math.max(8, d.size / 4) + "px")
            .text(d => d.id);

        // 타이틀 (노드 아래)
        node.append("text")
            .attr("dy", d => d.size + 14)
            .attr("text-anchor", "middle")
            .attr("class", "node-label")
            .style("font-size", "9px")
            .style("fill", "#94a3b8")
            .text(d => d.label.length > 25 ? d.label.substring(0, 25) + "..." : d.label);

        const tooltip = d3.select("#tooltip");

        node.on("mouseover", (event, d) => {{
            tooltip.style("opacity", 1)
                .html(`<div class="key">${{d.id}}</div>
                       <div class="summary">${{d.label}}</div>
                       <div class="meta">${{d.type}} · ${{d.status}}</div>`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
        }})
        .on("mouseout", () => tooltip.style("opacity", 0))
        .on("click", (event, d) => {{
            window.open(jiraUrl + "/browse/" + d.id, "_blank");
        }});

        simulation.on("tick", () => {{
            // 링크 끝점을 노드 가장자리에 맞춤
            link.each(function(d) {{
                const dx = d.target.x - d.source.x;
                const dy = d.target.y - d.source.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist === 0) return;
                const sourceR = d.source.size || 25;
                const targetR = d.target.size || 25;
                d.sourceX = d.source.x + (dx / dist) * sourceR;
                d.sourceY = d.source.y + (dy / dist) * sourceR;
                d.targetX = d.target.x - (dx / dist) * (targetR + 8);
                d.targetY = d.target.y - (dy / dist) * (targetR + 8);
            }});

            link
                .attr("x1", d => d.sourceX)
                .attr("y1", d => d.sourceY)
                .attr("x2", d => d.targetX)
                .attr("y2", d => d.targetY);

            linkLabel
                .attr("x", d => (d.source.x + d.target.x) / 2)
                .attr("y", d => (d.source.y + d.target.y) / 2);

            node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});

        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}

        // Initial zoom to fit
        setTimeout(() => {{
            const bounds = g.node().getBBox();
            const fullWidth = bounds.width;
            const fullHeight = bounds.height;
            const midX = bounds.x + fullWidth / 2;
            const midY = bounds.y + fullHeight / 2;
            const scale = 0.7 / Math.max(fullWidth / width, fullHeight / height);
            const translate = [width / 2 - scale * midX, height / 2 - scale * midY];
            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
            );
        }}, 1000);
    </script>
</body>
</html>'''

        # 파일로 저장
        if output_path:
            file_path = Path(output_path)
        else:
            file_path = Path(settings.data_path) / "jira_graphs" / f"{issue_key}_graph.html"

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_template)

        return {
            "issue_key": issue_key,
            "file_path": str(file_path),
            "node_count": len(graph_data["nodes"]),
            "link_count": len(graph_data["links"]),
            "message": f"그래프가 생성되었습니다. 브라우저에서 열어보세요: {file_path}",
        }

    def analyze_jira_image(self, issue_key: str, attachment_index: int = 0, prompt: str = "이 이미지를 분석해주세요.") -> dict:
        """Jira 이슈의 첨부 이미지를 분석합니다."""
        import requests
        from requests.auth import HTTPBasicAuth
        import base64

        if not settings.jira_url or not settings.jira_email or not settings.jira_api_token:
            return {"error": "Jira API 설정이 없습니다."}

        auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
        headers = {"Accept": "application/json"}

        try:
            # 이슈에서 첨부파일 정보 가져오기
            url = f"{settings.jira_url}/rest/api/3/issue/{issue_key}?fields=attachment"
            response = requests.get(url, headers=headers, auth=auth, timeout=30)
            if response.status_code != 200:
                return {"error": f"이슈 조회 실패: {response.status_code}"}

            attachments = response.json().get("fields", {}).get("attachment", [])
            # 이미지 타입만 필터링
            image_attachments = [a for a in attachments if a.get("mimeType", "").startswith("image/")]

            if not image_attachments:
                return {"error": "이미지 첨부파일이 없습니다."}

            if attachment_index >= len(image_attachments):
                return {"error": f"첨부파일 인덱스 초과. 이미지 {len(image_attachments)}개 있음."}

            attachment = image_attachments[attachment_index]
            image_url = attachment.get("content")
            filename = attachment.get("filename")
            mime_type = attachment.get("mimeType")

            # 이미지 다운로드
            img_response = requests.get(image_url, auth=auth, timeout=60)
            if img_response.status_code != 200:
                return {"error": f"이미지 다운로드 실패: {img_response.status_code}"}

            # 이미지 리사이즈 (최대 2048px)
            from io import BytesIO
            from PIL import Image

            img = Image.open(BytesIO(img_response.content))
            max_size = 2048
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)

            # PNG로 변환 후 base64 인코딩
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            mime_type = "image/png"  # 리사이즈 후 PNG로 통일

            # LLM으로 이미지 분석
            from agent.llm import llm_client

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Jira 이슈 {issue_key}의 첨부 이미지 '{filename}'입니다.\n\n{prompt}"
                        }
                    ]
                }
            ]

            llm_response = llm_client.chat(messages)
            analysis = llm_response.choices[0].message.content

            return {
                "issue_key": issue_key,
                "filename": filename,
                "analysis": analysis,
            }
        except Exception as e:
            return {"error": str(e)}

    def _extract_jira_description(self, description: dict | None) -> str | None:
        """Jira ADF (Atlassian Document Format) 형식의 description을 텍스트로 변환
        링크도 함께 추출하여 텍스트에 포함"""
        if not description:
            return None
        if isinstance(description, str):
            return description

        # ADF 형식 파싱 (링크 포함)
        def extract_text(node: dict) -> str:
            if node.get("type") == "text":
                text = node.get("text", "")
                # 링크가 있으면 URL도 추가
                marks = node.get("marks", [])
                for mark in marks:
                    if mark.get("type") == "link":
                        href = mark.get("attrs", {}).get("href", "")
                        if href and href not in text:
                            text = f"{text} ({href})"
                return text
            if "content" in node:
                return "".join(extract_text(child) for child in node["content"])
            return ""

        try:
            return extract_text(description).strip()
        except Exception:
            return str(description)

    def sync_task_status(self, project: str, task_name: str | None = None) -> dict:
        """GitHub PR 상태를 확인하여 태스크 상태를 동기화합니다."""
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if proj.get("deleted"):
            return {"error": f"프로젝트 '{project}'은(는) 삭제된 상태입니다."}

        tasks = proj.get("tasks", {})
        if not tasks:
            return {"error": "동기화할 태스크가 없습니다."}

        # 특정 태스크만 또는 전체
        target_tasks = {task_name: tasks[task_name]} if task_name else tasks
        if task_name and task_name not in tasks:
            return {"error": f"태스크 '{task_name}'을(를) 찾을 수 없습니다."}

        repo_path = proj["repo_path"]
        machine = proj.get("machine", "local")
        results = []

        for t_name, task in target_tasks.items():
            branch = task.get("branch", t_name)
            old_status = task.get("status", "pending")

            # PR 상태 조회
            pr_info = self._get_pr_status(repo_path, branch, machine)

            if pr_info.get("error"):
                results.append({
                    "task": t_name,
                    "status": old_status,
                    "pr": None,
                    "note": pr_info["error"]
                })
                continue

            # PR 상태에 따라 태스크 상태 결정
            new_status = old_status
            if pr_info.get("state") == "MERGED":
                new_status = "completed"
            elif pr_info.get("state") == "OPEN":
                new_status = "in_review"
            elif pr_info.get("state") == "CLOSED":
                # 머지 안 하고 닫힌 경우는 in_progress로 되돌림
                new_status = "in_progress"

            # 상태 업데이트
            if new_status != old_status:
                task["status"] = new_status

            # PR 정보 저장 (PR이 있으면 항상 저장)
            if pr_info.get("number"):
                task["pr"] = {
                    "number": pr_info.get("number"),
                    "url": pr_info.get("url"),
                    "state": pr_info.get("state"),  # OPEN / MERGED / CLOSED
                    "title": pr_info.get("title"),
                }

            results.append({
                "task": t_name,
                "branch": branch,
                "old_status": old_status,
                "new_status": new_status,
                "changed": new_status != old_status,
                "pr": task.get("pr")
            })

        self._save(data)

        changed_count = sum(1 for r in results if r.get("changed"))
        return {
            "success": True,
            "project": project,
            "synced": len(results),
            "changed": changed_count,
            "results": results
        }

    def _get_pr_status(self, repo_path: str, branch: str, machine: str) -> dict:
        """gh CLI로 PR 상태 조회"""
        is_local = machine == "local" or machine.lower() == settings.local_machine.lower()

        # gh pr list로 해당 브랜치의 PR 조회
        gh_cmd = f'gh pr list --head "{branch}" --state all --json number,title,state,url --limit 1'

        if is_local:
            try:
                result = subprocess.run(
                    gh_cmd,
                    shell=True,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    return {"error": f"gh 명령 실패: {result.stderr}"}
                return self._parse_pr_result(result.stdout)
            except Exception as e:
                return {"error": str(e)}
        else:
            # 원격 실행
            resolved_host = self._resolve_host(machine)
            if isinstance(resolved_host, dict):
                return resolved_host

            repo_path = repo_path.replace("~", "$HOME")
            script = f'''
# homebrew PATH 추가 (macOS)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd {repo_path} || exit 1
{gh_cmd}
'''
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", resolved_host, script]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    return {"error": f"원격 gh 명령 실패: {result.stderr or result.stdout}"}
                return self._parse_pr_result(result.stdout)
            except Exception as e:
                return {"error": str(e)}

    def _parse_pr_result(self, output: str) -> dict:
        """gh CLI 출력을 파싱"""
        import json as json_module
        try:
            prs = json_module.loads(output)
            if not prs:
                return {"error": "PR 없음"}
            pr = prs[0]
            return {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "state": pr.get("state"),  # OPEN, CLOSED, MERGED
                "url": pr.get("url")
            }
        except Exception as e:
            return {"error": f"파싱 오류: {e}"}

    def list_branches(self, project: str, pattern: str | None = None, remote_only: bool = False) -> dict:
        """프로젝트의 Git 브랜치 목록을 조회합니다."""
        data = self._load()
        if project not in data["projects"]:
            return {"error": f"프로젝트 '{project}'을(를) 찾을 수 없습니다."}

        proj = data["projects"][project]
        if proj.get("deleted"):
            return {"error": f"프로젝트 '{project}'은(는) 삭제된 상태입니다."}

        repo_path = proj["repo_path"]
        machine = proj.get("machine", "local")

        is_local = machine == "local" or machine.lower() == settings.local_machine.lower()

        # git branch 명령어 구성
        if remote_only:
            git_cmd = "git branch -r"
        else:
            git_cmd = "git branch -a"

        if is_local:
            try:
                result = subprocess.run(
                    git_cmd,
                    shell=True,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    return {"error": f"git 명령 실패: {result.stderr}"}
                return self._parse_branches(result.stdout, pattern, project)
            except Exception as e:
                return {"error": str(e)}
        else:
            # 원격 실행
            resolved_host = self._resolve_host(machine)
            if isinstance(resolved_host, dict):
                return resolved_host

            repo_path = repo_path.replace("~", "$HOME")
            script = f'''
# homebrew PATH 추가 (macOS)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd {repo_path} || exit 1
git fetch --prune 2>/dev/null
{git_cmd}
'''
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", resolved_host, script]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    return {"error": f"원격 git 명령 실패: {result.stderr or result.stdout}"}
                return self._parse_branches(result.stdout, pattern, project)
            except Exception as e:
                return {"error": str(e)}

    def _parse_branches(self, output: str, pattern: str | None, project: str) -> dict:
        """git branch 출력을 파싱"""
        branches = []
        current_branch = None

        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # 현재 브랜치 표시 (*) 처리
            is_current = line.startswith("*")
            if is_current:
                line = line[1:].strip()
                current_branch = line

            # remotes/origin/HEAD -> origin/main 같은 건 스킵
            if " -> " in line:
                continue

            # remotes/origin/ 접두사 정리
            if line.startswith("remotes/"):
                line = line[8:]  # "remotes/" 제거

            # 패턴 필터링
            if pattern and pattern.lower() not in line.lower():
                continue

            branches.append(line)

        # 중복 제거 및 정렬
        branches = sorted(set(branches))

        return {
            "project": project,
            "pattern": pattern,
            "current_branch": current_branch,
            "branches": branches,
            "count": len(branches)
        }


    # =====================
    # Notion MCP 연동
    # =====================

    def _get_notion_token(self) -> dict | None:
        """mcp-remote가 저장한 Notion OAuth 토큰을 가져옵니다."""
        mcp_auth_dir = Path.home() / ".mcp-auth"
        if not mcp_auth_dir.exists():
            return None

        # 최신 버전 디렉토리 찾기
        latest_dir = None
        latest_version = (0, 0, 0)
        for d in mcp_auth_dir.iterdir():
            if d.is_dir() and d.name.startswith("mcp-remote-"):
                try:
                    version_str = d.name.replace("mcp-remote-", "")
                    version = tuple(int(x) for x in version_str.split("."))
                    if version > latest_version:
                        latest_version = version
                        latest_dir = d
                except ValueError:
                    continue

        if not latest_dir:
            return None

        # tokens.json 찾기
        for f in latest_dir.iterdir():
            if f.name.endswith("_tokens.json"):
                try:
                    with open(f, "r") as file:
                        tokens = json.load(file)
                        if tokens.get("access_token"):
                            return tokens
                except Exception:
                    continue
        return None

    _notion_session_id: str | None = None

    def _parse_sse_response(self, text: str) -> dict | None:
        """SSE 형식 응답에서 JSON 데이터 추출"""
        for line in text.split("\n"):
            if line.startswith("data: "):
                try:
                    return json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
        return None

    def _notion_mcp_init(self) -> str | None:
        """MCP 세션 초기화하고 세션 ID 반환"""
        tokens = self._get_notion_token()
        if not tokens:
            return None

        access_token = tokens.get("access_token")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pm-agent", "version": "1.0.0"}
            }
        }

        try:
            response = requests.post(
                "https://mcp.notion.com/mcp",
                headers=headers,
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                return response.headers.get("mcp-session-id")
        except Exception:
            pass
        return None

    def _notion_mcp_call(self, method: str, params: dict | None = None) -> dict:
        """Notion MCP 서버에 JSON-RPC 호출"""
        tokens = self._get_notion_token()
        if not tokens:
            return {"error": "Notion OAuth 토큰이 없습니다. Claude Code에서 Notion MCP를 먼저 연결해주세요."}

        # 세션 ID 없으면 초기화
        if not self._notion_session_id:
            self._notion_session_id = self._notion_mcp_init()
            if not self._notion_session_id:
                return {"error": "Notion MCP 세션 초기화 실패"}

        access_token = tokens.get("access_token")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": self._notion_session_id,
        }

        # JSON-RPC 2.0 요청
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": method,
            "params": params or {}
        }

        try:
            response = requests.post(
                "https://mcp.notion.com/mcp",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 401:
                self._notion_session_id = None  # 세션 리셋
                return {"error": "Notion 인증 만료. Claude Code에서 Notion MCP를 다시 연결해주세요."}

            if response.status_code != 200:
                return {"error": f"Notion MCP 오류: {response.status_code} - {response.text}"}

            # SSE 형식 응답 파싱
            result = self._parse_sse_response(response.text)
            if not result:
                return {"error": "응답 파싱 실패", "raw": response.text[:500]}

            if "error" in result:
                return {"error": f"MCP 오류: {result['error']}"}

            return result.get("result", result)
        except requests.exceptions.Timeout:
            return {"error": "Notion MCP 타임아웃"}
        except Exception as e:
            return {"error": str(e)}

    def get_notion_page(self, page_url_or_id: str) -> dict:
        """Notion 페이지 내용을 가져옵니다.

        Args:
            page_url_or_id: Notion 페이지 URL 또는 ID
        """
        result = self._notion_mcp_call("tools/call", {
            "name": "notion-fetch",
            "arguments": {"id": page_url_or_id}
        })

        if "error" in result:
            return result

        # 결과 파싱
        content = result.get("content", [])
        if content and len(content) > 0:
            text_content = content[0].get("text", "")
            return {
                "page_url": page_url_or_id,
                "content": text_content,
            }

        return {"error": "페이지 내용을 가져올 수 없습니다.", "raw": result}

    def search_notion(self, query: str, page_url: str | None = None) -> dict:
        """Notion에서 검색합니다.

        Args:
            query: 검색어
            page_url: 특정 페이지 내에서 검색 (선택)
        """
        params = {"query": query}
        if page_url:
            params["page_url"] = page_url

        result = self._notion_mcp_call("tools/call", {
            "name": "notion-search",
            "arguments": params
        })

        if "error" in result:
            return result

        content = result.get("content", [])
        if content and len(content) > 0:
            text_content = content[0].get("text", "")
            return {
                "query": query,
                "results": text_content,
            }

        return {"error": "검색 결과가 없습니다.", "raw": result}


# 싱글톤 인스턴스
state_manager = StateManager()
