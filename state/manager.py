import os
import subprocess
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
        """브랜치 이름을 디렉토리명으로 사용 가능하게 변환"""
        # feature/foo-bar -> feature-foo-bar
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
        sanitized = self._sanitize_branch_name(branch)
        # 워크트리 폴더 구조: {repo}-worktrees/{branch}
        worktrees_dir = f"{repo_path}-worktrees"
        worktree_path = f"{worktrees_dir}/{sanitized}"

        # 머신에 따라 로컬/원격 실행
        if machine == "local":
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


# 싱글톤 인스턴스
state_manager = StateManager()
