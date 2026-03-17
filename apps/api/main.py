import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api import router as api_router
from config import settings


# Request/Response 모델
import re


def extract_jira_keys(text: str) -> list[str]:
    """텍스트에서 Jira 이슈 키 추출 (예: PRDEL-123, PROJ-456)"""
    pattern = r'\b([A-Z][A-Z0-9]+-\d+)\b'
    return list(set(re.findall(pattern, text)))


def extract_notion_urls(text: str) -> list[str]:
    """텍스트에서 Notion URL 추출"""
    pattern = r'https?://(?:www\.)?notion\.so/[^\s<>"\']+'
    return list(set(re.findall(pattern, text)))


def extract_pr_info(url: str) -> tuple[str, str, int] | None:
    """GitHub PR URL에서 owner, repo, pr_number 추출
    예: https://github.com/owner/repo/pull/33
    """
    pattern = r'https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
    match = re.match(pattern, url)
    if match:
        return match.group(1), match.group(2), int(match.group(3))
    return None


def get_pr_head_branch(owner: str, repo: str, pr_number: int) -> str | None:
    """GitHub API로 PR의 head 브랜치 조회"""
    import subprocess
    try:
        result = subprocess.run(
            ["gh", "api", f"/repos/{owner}/{repo}/pulls/{pr_number}", "--jq", ".head.ref"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.error(f"PR 브랜치 조회 실패: {e}")
    return None


class AddProjectRequest(BaseModel):
    repo_path: str
    machine: str = "local"
    title: str | None = None


class BranchSuggestRequest(BaseModel):
    project: str
    description: str


class BranchSuggestion(BaseModel):
    type: str
    name: str
    full: str
    reason: str


class BranchSuggestResponse(BaseModel):
    suggestions: list[BranchSuggestion]
    detected_jira_keys: list[str] = []
    detected_notion_urls: list[str] = []


class CreateTaskRequest(BaseModel):
    project: str
    branch: str
    description: str
    base_branch: str | None = None  # base 브랜치명 또는 PR URL


class CreateTaskResponse(BaseModel):
    success: bool
    worktree_path: str | None = None
    task_name: str | None = None
    jira_key: str | None = None
    notion_urls: list[str] = []
    claude_command: str | None = None
    error: str | None = None
    warning: str | None = None

app = FastAPI(
    title="Worktreee",
    description="Worktreee - OpenAI 호환 API",
    version="0.1.0",
)

# CORS 설정
class IDEPathRequest(BaseModel):
    project: str
    project_path: str = None


@app.post("/api/projects/ide-path")
async def get_ide_path(request: IDEPathRequest):
    """IDE 열기에 필요한 연결 정보 반환.
    - 브라우저와 같은 머신(mac) → is_local: true (idea:// 스킴)
    - 그 외(nuc 등) → SSH 연결 정보 (jetbrains-gateway:// 스킴, 프론트에서 조합)
    """
    from state.manager import StateManager

    sm = StateManager()
    data = sm._load()

    if request.project not in data.get("projects", {}):
        return {"error": f"프로젝트 '{request.project}' 없음"}

    project = data["projects"][request.project]
    machine = project.get("machine", "local")
    client_machine = os.getenv("CLIENT_MACHINE", "mac")
    project_path = request.project_path or project["repo_path"]

    # 브라우저와 같은 머신이면 idea:// 스킴으로 직접 열기
    if machine == "local" or machine == client_machine:
        return {
            "success": True,
            "is_local": True,
            "project_path": project_path
        }

    # 원격: SSH 연결 정보 + IDE 경로 탐색
    import subprocess
    remote_hosts = os.getenv("REMOTE_HOSTS", "")
    local_machine = os.getenv("LOCAL_MACHINE", "local")
    host_map = {}
    for entry in remote_hosts.split(","):
        if ":" in entry:
            alias, addr = entry.split(":", 1)
            host_map[alias.strip()] = addr.strip()

    # API 서버 자신의 머신이면 LOCAL_SSH_ADDR 사용
    if machine == local_machine:
        local_ssh = os.getenv("LOCAL_SSH_ADDR", "")
        if "@" in local_ssh:
            user, host = local_ssh.split("@", 1)
        elif local_ssh:
            user, host = os.getenv("USER", "user"), local_ssh
        else:
            return {"error": "LOCAL_SSH_ADDR 환경변수가 설정되지 않았습니다."}
    elif machine in host_map:
        resolved = host_map[machine]
        if "@" in resolved:
            user, host = resolved.split("@", 1)
        else:
            user, host = os.getenv("USER", "user"), resolved
    else:
        return {"error": f"머신 '{machine}'의 SSH 주소를 찾을 수 없습니다. REMOTE_HOSTS를 확인하세요."}

    # 원격 IDE 백엔드 경로 탐색 (jg 방식)
    ide_path = None
    if machine == local_machine:
        # API 서버 자신 → 파일시스템에서 직접 탐색
        import glob
        home = os.getenv("HOME", f"/home/{user}")
        candidates = sorted(
            glob.glob(f"{home}/.cache/JetBrains/RemoteDev/dist/*idea*"),
            reverse=True
        )
        if candidates:
            ide_path = candidates[0]
    else:
        # 원격 머신 → SSH로 탐색
        ssh_target = f"{user}@{host}"
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                 ssh_target,
                 "ls -d ~/.cache/JetBrains/RemoteDev/dist/*idea* 2>/dev/null | sort -r | head -1"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                ide_path = result.stdout.strip()
        except Exception:
            pass

    resp = {
        "success": True,
        "is_local": False,
        "user": user,
        "host": host,
        "port": 22,
        "project_path": project_path
    }
    if ide_path:
        resp["ide_path"] = ide_path
    return resp


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router)

# 정적 파일 서빙 (Jira 그래프 HTML 등)
graphs_dir = Path(settings.data_path) / "jira_graphs"
graphs_dir.mkdir(parents=True, exist_ok=True)


# ============ JSON API 엔드포인트 ============

@app.get("/api/projects")
async def api_list_projects():
    """프로젝트 목록 API (JSON)"""
    from state.manager import StateManager

    sm = StateManager()
    data = sm._load()

    projects = []
    for name, info in data.get('projects', {}).items():
        if info.get('deleted_at'):
            continue

        tasks = []
        for task_name, task in info.get('tasks', {}).items():
            tasks.append({
                "name": task_name,
                "branch": task.get('branch', ''),
                "status": task.get('status', 'pending'),
                "jira_key": task.get('jira_key'),
                "context": task.get('context'),
                "worktree": task.get('worktree'),
                "created": task.get('created'),
                "archived_at": task.get('archived_at'),
                "pr": task.get('pr'),
            })

        projects.append({
            "name": name,
            "title": info.get('title'),
            "repo_path": info.get('repo_path', ''),
            "machine": info.get('machine', ''),
            "task_count": len(tasks),
            "tasks": tasks,
        })

    return {"projects": projects}


@app.get("/api/archived-projects")
async def api_archived_projects():
    """아카이브된 프로젝트 목록"""
    from state.manager import StateManager

    sm = StateManager()
    data = sm._load()

    projects = []
    for name, info in data.get('projects', {}).items():
        if not info.get('deleted_at'):
            continue

        tasks = []
        for task_name, task in info.get('tasks', {}).items():
            tasks.append({
                "name": task_name,
                "branch": task.get('branch', ''),
                "status": task.get('status', 'pending'),
                "worktree": task.get('worktree'),
                "created": task.get('created'),
                "pr": task.get('pr'),
            })

        projects.append({
            "name": name,
            "title": info.get('title'),
            "repo_path": info.get('repo_path', ''),
            "machine": info.get('machine', ''),
            "task_count": len(tasks),
            "tasks": tasks,
            "deleted_at": info.get('deleted_at'),
        })

    return {"projects": projects}


@app.get("/api/graphs")
async def api_list_graphs():
    """그래프 목록 API (JSON)"""
    from datetime import datetime
    import requests
    from requests.auth import HTTPBasicAuth

    files = sorted(graphs_dir.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)

    # Jira에서 이슈 제목 가져오기
    issue_keys = [f.stem.replace("_graph", "") for f in files]
    titles = {}
    if issue_keys:
        try:
            jql = f"key in ({','.join(issue_keys)})"
            resp = requests.post(
                f"{settings.jira_url}/rest/api/3/search/jql",
                auth=HTTPBasicAuth(settings.jira_email, settings.jira_api_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json={"jql": jql, "fields": ["summary"], "maxResults": 100},
                timeout=10
            )
            if resp.status_code == 200:
                for issue in resp.json().get("issues", []):
                    titles[issue["key"]] = issue["fields"]["summary"]
        except Exception:
            pass

    graphs = []
    for f in files:
        key = f.stem.replace("_graph", "")
        graphs.append({
            "filename": f.name,
            "issue_key": key,
            "title": titles.get(key),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })

    return {"graphs": graphs}


# 그래프 HTML 파일 서빙 (없으면 자동 생성)
@app.get("/api/graphs/files/{filename}")
async def get_graph_file(filename: str):
    """그래프 파일 반환 (없으면 자동 생성)"""
    from fastapi.responses import FileResponse, HTMLResponse
    from state.manager import StateManager

    file_path = graphs_dir / filename

    # 파일이 없으면 생성 시도
    if not file_path.exists() and filename.endswith("_graph.html"):
        issue_key = filename.replace("_graph.html", "")
        sm = StateManager()
        result = sm.get_jira_graph_html(issue_key, include_notion=True)

        if "error" in result or "_error" in result:
            return HTMLResponse(
                content=f"<html><body><h1>Graph 생성 실패</h1><p>{result.get('error') or result.get('_error')}</p><p><a href='{settings.jira_url}/browse/{issue_key}'>Jira에서 보기</a></p></body></html>",
                status_code=404
            )

    if file_path.exists():
        return FileResponse(file_path, media_type="text/html")

    return HTMLResponse(content="<html><body><h1>Not Found</h1></body></html>", status_code=404)


@app.delete("/api/graphs/{issue_key}")
async def delete_graph(issue_key: str):
    """그래프 파일 삭제"""
    filename = f"{issue_key}_graph.html"
    file_path = graphs_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Graph not found")

    try:
        file_path.unlink()
        return {"success": True, "message": f"{issue_key} 그래프가 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graphs/sync-stream/{issue_key}")
async def sync_graph_stream(issue_key: str):
    """단일 이슈 그래프 재생성 (SSE 스트림)"""
    from fastapi.responses import StreamingResponse
    from state.manager import StateManager
    import json as json_module
    import queue
    import threading

    progress_queue = queue.Queue()

    def on_progress(event_type: str, key: str, detail: str | None):
        progress_queue.put({"type": event_type, "key": key, "detail": detail})

    def generate():
        sm = StateManager()

        # 별도 스레드에서 sync 실행
        result_holder = [None]
        def run_sync():
            result_holder[0] = sm.get_jira_graph_html(issue_key, include_notion=True, on_progress=on_progress)
            progress_queue.put(None)  # 종료 신호

        thread = threading.Thread(target=run_sync)
        thread.start()

        # 진행 상태 스트리밍
        while True:
            try:
                item = progress_queue.get(timeout=60)
                if item is None:
                    break
                yield f"data: {json_module.dumps(item, ensure_ascii=False)}\n\n"
            except queue.Empty:
                break

        thread.join()

        # 최종 결과
        result = result_holder[0]
        if result and ("error" in result or "_error" in result):
            yield f"data: {json_module.dumps({'type': 'error', 'detail': result.get('error') or result.get('_error')}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json_module.dumps({'type': 'done', 'key': issue_key}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/graphs/sync/{issue_key}")
async def sync_single_graph(issue_key: str):
    """단일 이슈 그래프 재생성"""
    from state.manager import StateManager

    sm = StateManager()
    result = sm.get_jira_graph_html(issue_key, include_notion=True)

    if "error" in result or "_error" in result:
        return {"success": False, "error": result.get("error") or result.get("_error")}

    return {"success": True, "issue_key": issue_key, "message": f"{issue_key} graph updated"}


@app.post("/api/graphs/sync")
async def sync_graphs():
    """기존 그래프들을 Jira와 동기화 (변경된 것만 재생성)"""
    import requests
    from requests.auth import HTTPBasicAuth
    from datetime import datetime
    from state.manager import StateManager

    sm = StateManager()
    results = {"updated": [], "skipped": [], "errors": []}

    # 기존 그래프 파일들 확인
    graph_files = list(graphs_dir.glob("*.html"))
    if not graph_files:
        return {"message": "No graphs to sync", "results": results}

    auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
    headers = {"Accept": "application/json"}

    for graph_file in graph_files:
        issue_key = graph_file.stem.replace("_graph", "")
        file_mtime = datetime.fromtimestamp(graph_file.stat().st_mtime)

        try:
            # Jira에서 이슈 updated 시간 확인
            resp = requests.get(
                f"{settings.jira_url}/rest/api/3/issue/{issue_key}",
                auth=auth,
                headers=headers,
                params={"fields": "updated"},
                timeout=10
            )

            if resp.status_code != 200:
                results["errors"].append(f"{issue_key}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            updated_str = data.get("fields", {}).get("updated", "")
            jira_updated = datetime.fromisoformat(updated_str.replace("+0900", "+09:00").replace("+0000", "+00:00"))
            jira_updated = jira_updated.replace(tzinfo=None)

            if jira_updated > file_mtime:
                result = sm.get_jira_graph_html(issue_key, include_notion=True)
                if "error" in result or "_error" in result:
                    results["errors"].append(f"{issue_key}: {result.get('error') or result.get('_error')}")
                else:
                    results["updated"].append(issue_key)
            else:
                results["skipped"].append(issue_key)

        except Exception as e:
            results["errors"].append(f"{issue_key}: {str(e)}")

    return {
        "message": f"Sync complete: {len(results['updated'])} updated, {len(results['skipped'])} skipped, {len(results['errors'])} errors",
        "results": results
    }


@app.post("/api/add-project")
async def add_project(request: AddProjectRequest):
    """새 프로젝트 추가"""
    import subprocess
    import os
    from state.manager import StateManager

    machine = request.machine
    repo_path = request.repo_path

    # repo_path가 실제 Git 레포인지 검증
    try:
        if machine == "local" or machine == os.getenv("LOCAL_MACHINE", "nuc"):
            if not Path(repo_path).is_dir():
                return {"success": False, "error": f"경로가 존재하지 않습니다: {repo_path}"}
            result = subprocess.run(
                ["git", "-C", repo_path, "rev-parse", "--git-dir"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return {"success": False, "error": f"Git 레포가 아닙니다: {repo_path}"}
        else:
            remote_hosts = os.getenv("REMOTE_HOSTS", "")
            host_map = {}
            for entry in remote_hosts.split(","):
                if ":" in entry:
                    alias, addr = entry.split(":", 1)
                    host_map[alias.strip()] = addr.strip()

            resolved_host = host_map.get(machine, machine)
            remote_path = repo_path.replace("~", "$HOME")

            script = f'test -d {remote_path} && git -C {remote_path} rev-parse --git-dir > /dev/null 2>&1 && echo OK'
            result = subprocess.run(
                ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", resolved_host, script],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0 or "OK" not in result.stdout:
                return {"success": False, "error": f"원격 Git 레포를 찾을 수 없습니다 ({machine}): {repo_path}"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"경로 확인 타임아웃 ({machine})"}
    except Exception as e:
        return {"success": False, "error": f"경로 확인 실패: {str(e)}"}

    # repo_path에서 프로젝트 이름 자동 생성
    name = Path(repo_path).name
    sm = StateManager()
    data = sm._load()
    if name in data.get("projects", {}):
        name = f"{name}-{machine}"

    result = sm.add_project(
        name=name,
        repo_path=request.repo_path,
        machine=request.machine,
        title=request.title,
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {"success": True, "project": result.get("project")}


@app.post("/api/suggest-branch-names", response_model=BranchSuggestResponse)
async def suggest_branch_names(request: BranchSuggestRequest):
    """AI 기반 브랜치 이름 추천 (Jira 키, Notion URL 자동 감지 + Jira 내용 조회)"""
    from agent.llm import llm_client
    from state.manager import StateManager

    # 자동 감지
    jira_keys = extract_jira_keys(request.description)
    notion_urls = extract_notion_urls(request.description)
    jira_key = jira_keys[0] if jira_keys else None

    # Jira 이슈 내용 조회
    jira_context = ""
    if jira_key:
        sm = StateManager()
        jira_issue = sm.get_jira_issue(jira_key, include_children=False, recursive=False, fetch_notion=False)
        if jira_issue and "error" not in jira_issue:
            summary = jira_issue.get("summary", "")
            description = (jira_issue.get("description") or "")[:500]  # 너무 길면 자르기
            issue_type = jira_issue.get("issue_type", "")
            jira_context = f"""
=== Jira 이슈 정보 ({jira_key}) ===
제목: {summary}
타입: {issue_type}
설명: {description}
================================"""

    # Jira 키가 있으면 브랜치에 포함하도록 안내
    jira_instruction = ""
    if jira_key:
        jira_instruction = f"""
IMPORTANT: Jira 티켓 {jira_key}가 감지되었습니다.
- 모든 추천에 반드시 "{jira_key}" 를 포함해야 합니다
- 형식: {{type}}/{jira_key}/{{slug}} (예: feat/{jira_key}/invite-feature)
- 브랜치 이름은 Jira 이슈 내용을 정확히 반영해야 합니다"""

    prompt = f"""당신은 git 브랜치 네이밍 전문가입니다.

작업 설명: {request.description}
프로젝트: {request.project}
{jira_context}
{jira_instruction}

다음 규칙에 따라 3개의 브랜치 이름을 추천해주세요:

브랜치 타입:
- feat: 새로운 기능
- fix: 버그 수정
- chore: 설정, 빌드, 린트, 의존성
- refactor: 리팩토링
- docs: 문서

규칙:
1. 형식: {{type}}/{{kebab-case-description}}
2. 영어 사용, 소문자만
3. 간결하고 명확하게 (2-4 단어)
4. 특수문자 제외 (하이픈만 허용)
5. 작업 내용을 정확히 반영

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
[
  {{"type": "feat", "name": "user-auth-flow", "full": "feat/user-auth-flow", "reason": "이유"}},
  {{"type": "feat", "name": "add-login", "full": "feat/add-login", "reason": "이유"}},
  {{"type": "feat", "name": "auth-system", "full": "feat/auth-system", "reason": "이유"}}
]"""

    try:
        response = llm_client.chat(
            [{"role": "user", "content": prompt}],
            model="gemini-3-flash-preview"
        )
        content = response.choices[0].message.content.strip()

        # JSON 파싱 (코드 블록 제거)
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]

        suggestions = json.loads(content)
        return {
            "suggestions": suggestions,
            "detected_jira_keys": jira_keys,
            "detected_notion_urls": notion_urls,
        }
    except Exception as e:
        # 실패시 기본 추천 제공
        task_name = request.description.lower().replace(" ", "-")[:30]
        base_suggestions = [
            {"type": "feat", "name": task_name, "full": f"feat/{task_name}", "reason": "기본 추천"},
            {"type": "chore", "name": task_name, "full": f"chore/{task_name}", "reason": "설정/정리 작업인 경우"},
            {"type": "fix", "name": task_name, "full": f"fix/{task_name}", "reason": "버그 수정인 경우"},
        ]
        # Jira 키 있으면 첫 번째에 포함
        if jira_key:
            base_suggestions.insert(0, {
                "type": "feat",
                "name": f"{jira_key}/{task_name}",
                "full": f"feat/{jira_key}/{task_name}",
                "reason": f"Jira 티켓 {jira_key} 연결"
            })
        return {
            "suggestions": base_suggestions[:3],
            "detected_jira_keys": jira_keys,
            "detected_notion_urls": notion_urls,
        }


@app.post("/api/create-task", response_model=CreateTaskResponse)
async def create_task(request: CreateTaskRequest):
    """태스크 생성 및 워크트리 생성 (Jira 키, Notion URL 자동 감지)"""
    from state.manager import StateManager

    logger.info(f"[create-task] 시작: project={request.project}, branch={request.branch}, base={request.base_branch}")

    sm = StateManager()

    # base_branch 처리: PR URL이면 브랜치명 추출
    base_branch = None
    if request.base_branch:
        pr_info = extract_pr_info(request.base_branch)
        if pr_info:
            owner, repo, pr_number = pr_info
            logger.info(f"[create-task] PR URL 감지: {owner}/{repo}#{pr_number}")
            base_branch = get_pr_head_branch(owner, repo, pr_number)
            if base_branch:
                logger.info(f"[create-task] PR head 브랜치: {base_branch}")
            else:
                logger.warning(f"[create-task] PR 브랜치 조회 실패, base_branch 그대로 사용")
                base_branch = request.base_branch
        else:
            base_branch = request.base_branch
            logger.info(f"[create-task] base_branch: {base_branch}")

    # 자동 감지
    jira_keys = extract_jira_keys(request.description)
    notion_urls = extract_notion_urls(request.description)
    jira_key = jira_keys[0] if jira_keys else None
    logger.info(f"[create-task] 감지된 Jira: {jira_key}, Notion URLs: {notion_urls}")

    # 브랜치 이름에서 task name 추출 (feat/xxx → xxx)
    branch_parts = request.branch.split("/", 1)
    task_name = branch_parts[1] if len(branch_parts) > 1 else request.branch

    # 1. 태스크 생성
    result = sm.add_task(
        project=request.project,
        task_name=task_name,
        context=request.description,
        branch=request.branch,
        jira_key=jira_key,
        notion_urls=notion_urls if notion_urls else None,
        base_branch=base_branch,
    )
    logger.info(f"[create-task] add_task 결과: {result}")

    if "error" in result:
        logger.error(f"[create-task] 태스크 생성 실패: {result['error']}")
        return CreateTaskResponse(success=False, error=result["error"])

    # 2. 워크트리 생성 (base_branch 전달)
    worktree_result = sm.create_worktree(request.project, task_name, base_branch=base_branch)
    logger.info(f"[create-task] create_worktree 결과: {worktree_result}")

    warning = None
    if "error" in worktree_result:
        logger.warning(f"[create-task] 워크트리 생성 실패: {worktree_result['error']}")
        warning = f"태스크는 생성되었지만 워크트리 생성 실패: {worktree_result['error']}"

    # 3. Claude 세션 시작
    session_result = sm.start_claude_session(request.project, task_name)
    logger.info(f"[create-task] start_claude_session 결과: {session_result}")
    claude_command = session_result.get("command") if session_result.get("success") else None
    if not session_result.get("success"):
        session_error = session_result.get("error")
        if warning:
            warning += f"; Claude 세션 실패: {session_error}"
        else:
            warning = f"Claude 세션 실패: {session_error}"

    response = CreateTaskResponse(
        success=True,
        task_name=task_name,
        worktree_path=worktree_result.get("worktree"),
        jira_key=jira_key,
        notion_urls=notion_urls,
        claude_command=claude_command,
        warning=warning,
    )
    logger.info(f"[create-task] 최종 응답: success={response.success}, warning={response.warning}")
    return response

@app.get("/api/create-task-stream")
async def create_task_stream(
    project: str, 
    branch: str, 
    description: str, 
    base_branch: str | None = None
):
    """태스크 생성을 진행하며 단계별 상태를 SSE로 전송"""
    from fastapi.responses import StreamingResponse
    import json as json_module
    from state.manager import StateManager

    async def generate():
        sm = StateManager()
        
        # 1. 시작 알림
        yield f"data: {json_module.dumps({'type': 'info', 'message': '태스크 생성을 시작합니다...'}, ensure_ascii=False)}\n\n"
        
        # base_branch 처리 로직 (기존과 동일)
        actual_base = None
        if base_branch:
            pr_info = extract_pr_info(base_branch)
            if pr_info:
                yield f"data: {json_module.dumps({'type': 'info', 'message': 'GitHub PR 정보를 조회 중...'}, ensure_ascii=False)}\n\n"
                owner, repo, pr_number = pr_info
                actual_base = get_pr_head_branch(owner, repo, pr_number) or base_branch
            else:
                actual_base = base_branch

        # 2. 태스크 등록
        yield f"data: {json_module.dumps({'type': 'info', 'message': '프로젝트에 태스크 등록 중...'}, ensure_ascii=False)}\n\n"
        branch_parts = branch.split("/", 1)
        task_name = branch_parts[1] if len(branch_parts) > 1 else branch
        
        result = sm.add_task(
            project=project,
            task_name=task_name,
            context=description,
            branch=branch,
            jira_key=extract_jira_keys(description)[0] if extract_jira_keys(description) else None,
            notion_urls=extract_notion_urls(description),
            base_branch=actual_base,
        )
        
        if "error" in result:
            yield f"data: {json_module.dumps({'type': 'error', 'message': result['error']}, ensure_ascii=False)}\n\n"
            return

        # 3. 워크트리 생성
        yield f"data: {json_module.dumps({'type': 'info', 'message': 'Git 워크트리 생성 중 (시간이 소요될 수 있습니다)...'}, ensure_ascii=False)}\n\n"
        logger.info(f"[create-task] 워크트리 생성 시작: project={project}, task={task_name}, base={actual_base}")
        worktree_result = sm.create_worktree(project, task_name, base_branch=actual_base)

        if "error" in worktree_result:
            error_msg = worktree_result['error']
            logger.error(f"[create-task] 워크트리 생성 실패: project={project}, task={task_name}, error={error_msg}")
            yield f"data: {json_module.dumps({'type': 'warning', 'message': f'태스크는 생성되었으나 워크트리 생성 실패: {error_msg}'}, ensure_ascii=False)}\n\n"
        else:
            logger.info(f"[create-task] 워크트리 생성 완료: {worktree_result.get('worktree')}")
            yield f"data: {json_module.dumps({'type': 'info', 'message': '워크트리 생성 완료!'}, ensure_ascii=False)}\n\n"

        # 4. Claude 세션 시작
        yield f"data: {json_module.dumps({'type': 'info', 'message': 'Claude 사전 분석 세션 시작 중...'}, ensure_ascii=False)}\n\n"
        session_result = sm.start_claude_session(project, task_name)

        final_warning = None
        if not session_result.get("success"):
            final_warning = f"Claude 세션 시작 실패: {session_result.get('error')}"
            logger.error(f"[create-task] Claude 세션 실패: project={project}, task={task_name}, error={session_result.get('error')}")
            yield f"data: {json_module.dumps({'type': 'warning', 'message': final_warning}, ensure_ascii=False)}\n\n"

        # 5. 최종 결과 전송
        final_data = {
            "type": "done",
            "success": True,
            "task_name": task_name,
            "worktree_path": worktree_result.get("worktree"),
            "claude_command": session_result.get("command") if session_result.get("success") else f"cd {worktree_result.get('worktree')} && claude",
            "warning": final_warning
        }
        yield f"data: {json_module.dumps(final_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


class TaskActionRequest(BaseModel):
    project: str
    task_name: str


class TaskActionResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None


@app.post("/api/delete-task", response_model=TaskActionResponse)
async def delete_task(request: TaskActionRequest):
    """태스크 삭제 (워크트리 포함)"""
    from state.manager import StateManager

    sm = StateManager()
    result = sm.delete_task(request.project, request.task_name, cleanup_worktree=True)

    if "error" in result:
        return TaskActionResponse(success=False, error=result["error"])

    return TaskActionResponse(success=True, message=f"태스크 '{request.task_name}' 삭제됨")


@app.post("/api/archive-task", response_model=TaskActionResponse)
async def archive_task(request: TaskActionRequest):
    """태스크 아카이브"""
    from state.manager import StateManager

    sm = StateManager()
    result = sm.archive_task(request.project, request.task_name)

    if "error" in result:
        return TaskActionResponse(success=False, error=result["error"])

    return TaskActionResponse(success=True, message=f"태스크 '{request.task_name}' 아카이브됨")


@app.post("/api/restore-task", response_model=TaskActionResponse)
async def restore_task(request: TaskActionRequest):
    """아카이브된 태스크 복구"""
    from state.manager import StateManager

    sm = StateManager()
    result = sm.restore_task(request.project, request.task_name)

    if "error" in result:
        return TaskActionResponse(success=False, error=result["error"])

    return TaskActionResponse(success=True, message=f"태스크 '{request.task_name}' 복구됨")


class ProjectActionRequest(BaseModel):
    project: str


@app.post("/api/archive-project", response_model=TaskActionResponse)
async def archive_project(request: ProjectActionRequest):
    """프로젝트 아카이브 (soft delete)"""
    from state.manager import StateManager

    sm = StateManager()
    result = sm.delete_project(request.project)

    if "error" in result:
        return TaskActionResponse(success=False, error=result["error"])

    return TaskActionResponse(success=True, message=f"프로젝트 '{request.project}' 아카이브됨")


@app.post("/api/restore-project", response_model=TaskActionResponse)
async def restore_project(request: ProjectActionRequest):
    """아카이브된 프로젝트 복구"""
    from state.manager import StateManager

    sm = StateManager()
    result = sm.restore_project(request.project)

    if "error" in result:
        return TaskActionResponse(success=False, error=result["error"])

    return TaskActionResponse(success=True, message=f"프로젝트 '{request.project}' 복구됨")


class ClaudeSessionResponse(BaseModel):
    success: bool
    message: str | None = None
    analysis: str | None = None
    error: str | None = None


@app.post("/api/start-claude-session", response_model=ClaudeSessionResponse)
async def start_claude_session(request: TaskActionRequest):
    """태스크에 대한 Claude 세션 시작 (수동)"""
    from state.manager import StateManager

    sm = StateManager()
    result = sm.start_claude_session(request.project, request.task_name)

    if "error" in result:
        return ClaudeSessionResponse(success=False, error=result["error"])

    return ClaudeSessionResponse(
        success=True,
        message=result.get("message"),
        analysis=result.get("analysis"),
    )


@app.post("/api/sync-projects")
async def sync_projects():
    """모든 프로젝트의 메인 레포를 최신으로 동기화 (git fetch + pull)"""
    import subprocess
    import os

    from state.manager import StateManager

    sm = StateManager()
    data = sm._load()
    results = []

    for project_name, project in data.get("projects", {}).items():
        if project.get("deleted"):
            continue

        repo_path = project.get("repo_path")
        machine = project.get("machine", "local")

        if not repo_path:
            results.append({"project": project_name, "error": "repo_path 없음"})
            continue

        try:
            if machine == "local" or machine == os.getenv("LOCAL_MACHINE", "nuc"):
                # 로컬 실행 - gh CLI로 인증 설정
                env = os.environ.copy()
                env["GIT_ASKPASS"] = ""
                env["GIT_TERMINAL_PROMPT"] = "0"

                # gh를 credential helper로 설정하고 fetch/pull
                subprocess.run(
                    ["git", "-C", repo_path, "config", "credential.helper", "!gh auth git-credential"],
                    capture_output=True, text=True, timeout=10, env=env
                )
                # fetch
                subprocess.run(
                    ["git", "-C", repo_path, "fetch", "--prune"],
                    capture_output=True, text=True, timeout=30, env=env
                )
                # pull (현재 브랜치)
                result = subprocess.run(
                    ["git", "-C", repo_path, "pull", "--ff-only"],
                    capture_output=True, text=True, timeout=30, env=env
                )
                if result.returncode == 0:
                    results.append({"project": project_name, "success": True})
                else:
                    results.append({"project": project_name, "error": result.stderr.strip() or "pull 실패"})
            else:
                # SSH 원격 실행
                remote_hosts = os.getenv("REMOTE_HOSTS", "")
                host_map = {}
                for entry in remote_hosts.split(","):
                    if ":" in entry:
                        alias, addr = entry.split(":", 1)
                        host_map[alias.strip()] = addr.strip()

                resolved_host = host_map.get(machine, machine)
                remote_path = repo_path.replace("~", "$HOME")

                script = f'''
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd {remote_path} || exit 1
git fetch --prune
git pull --ff-only
'''
                cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", resolved_host, script]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    results.append({"project": project_name, "success": True})
                else:
                    results.append({"project": project_name, "error": result.stderr.strip() or "원격 pull 실패"})

        except subprocess.TimeoutExpired:
            results.append({"project": project_name, "error": "타임아웃"})
        except Exception as e:
            results.append({"project": project_name, "error": str(e)})

    success_count = sum(1 for r in results if r.get("success"))
    return {
        "success": True,
        "results": results,
        "synced": success_count,
        "total": len(results),
    }


class GitLogRequest(BaseModel):
    project: str
    limit: int = 30


@app.post("/api/git-log")
async def get_git_log(request: GitLogRequest):
    """프로젝트의 git log 그래프 반환"""
    import subprocess
    import os

    from state.manager import StateManager

    sm = StateManager()
    data = sm._load()

    if request.project not in data.get("projects", {}):
        return {"error": f"프로젝트 '{request.project}' 없음"}

    project = data["projects"][request.project]
    repo_path = project.get("repo_path")
    machine = project.get("machine", "local")

    if not repo_path:
        return {"error": "repo_path 없음"}

    try:
        # git log --graph 명령어
        git_cmd = [
            "git", "-C", repo_path,
            "log", "--graph", "--oneline", "--decorate", "--all",
            f"-{request.limit}"
        ]

        if machine == "local" or machine == os.getenv("LOCAL_MACHINE", "nuc"):
            # 로컬 실행
            result = subprocess.run(
                git_cmd,
                capture_output=True, text=True, timeout=30
            )
        else:
            # SSH 원격 실행
            remote_hosts = os.getenv("REMOTE_HOSTS", "")
            host_map = {}
            for entry in remote_hosts.split(","):
                if ":" in entry:
                    alias, addr = entry.split(":", 1)
                    host_map[alias.strip()] = addr.strip()

            resolved_host = host_map.get(machine, machine)
            remote_path = repo_path.replace("~", "$HOME")

            script = f'''
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd {remote_path} || exit 1
git log --graph --oneline --decorate --all -{request.limit}
'''
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", resolved_host, script]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return {"success": True, "log": result.stdout}
        else:
            return {"error": result.stderr.strip() or "git log 실패"}

    except subprocess.TimeoutExpired:
        return {"error": "타임아웃"}
    except Exception as e:
        return {"error": str(e)}


class PRInfoRequest(BaseModel):
    repo_path: str
    branch: str


class PRInfo(BaseModel):
    number: int | None = None
    state: str | None = None  # OPEN, MERGED, CLOSED
    url: str | None = None
    title: str | None = None
    draft: bool = False
    review_status: str | None = None  # APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED, None
    error: str | None = None


@app.post("/api/pr-info", response_model=PRInfo)
async def get_pr_info(request: PRInfoRequest):
    """브랜치의 GitHub PR 정보 조회"""
    import subprocess
    import re

    def try_gh_pr_list(repo: str, branch: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                "gh", "pr", "list",
                "--repo", repo,
                "--head", branch,
                "--state", "all",  # OPEN, MERGED, CLOSED 모두 포함
                "--json", "number,state,url,title,isDraft,reviewDecision",
                "--limit", "1"
            ],
            capture_output=True, text=True, timeout=10
        )

    try:
        repo = None

        # 1. 로컬 경로에서 git remote 추출 시도
        remote_result = subprocess.run(
            ["git", "-C", request.repo_path, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )
        if remote_result.returncode == 0:
            remote_url = remote_result.stdout.strip()
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    repo = remote_url.split(":")[-1].replace(".git", "")
                else:
                    repo = "/".join(remote_url.split("/")[-2:]).replace(".git", "")

        if not repo:
            return PRInfo()  # repo를 알 수 없음

        # GitHub PR 조회
        result = try_gh_pr_list(repo, request.branch)

        if result.returncode != 0:
            return PRInfo()

        prs = json.loads(result.stdout) if result.stdout.strip() else []

        if not prs:
            return PRInfo()  # PR 없음

        pr = prs[0]
        return PRInfo(
            number=pr.get("number"),
            state=pr.get("state"),
            url=pr.get("url"),
            title=pr.get("title"),
            draft=pr.get("isDraft", False),
            review_status=pr.get("reviewDecision")
        )

    except subprocess.TimeoutExpired:
        return PRInfo(error="Timeout")
    except Exception as e:
        return PRInfo(error=str(e))


@app.post("/api/sync-task-statuses")
async def sync_task_statuses():
    """모든 태스크의 상태를 GitHub PR 기반으로 동기화"""
    import subprocess
    import re
    from state.manager import StateManager

    def get_repo_from_path(repo_path: str) -> str | None:
        # 로컬 경로에서 git remote 추출
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                if "github.com" in remote_url:
                    if remote_url.startswith("git@"):
                        return remote_url.split(":")[-1].replace(".git", "")
                    else:
                        return "/".join(remote_url.split("/")[-2:]).replace(".git", "")
        except:
            pass
        return None

    def get_pr_info(repo: str, branch: str) -> dict | None:
        """PR 정보 조회 (저장용)"""
        try:
            result = subprocess.run(
                ["gh", "pr", "list", "--repo", repo, "--head", branch,
                 "--state", "all", "--json", "number,state,isDraft,url,title,reviewDecision", "--limit", "1"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                prs = json.loads(result.stdout)
                if prs:
                    pr = prs[0]
                    return {
                        "number": pr.get("number"),
                        "state": pr.get("state", "").upper(),
                        "url": pr.get("url"),
                        "title": pr.get("title"),
                        "draft": pr.get("isDraft", False),
                        "review_status": pr.get("reviewDecision"),
                    }
        except:
            pass
        return None

    def determine_status(pr_info: dict | None) -> str:
        """PR 상태 기반으로 태스크 상태 결정"""
        if not pr_info:
            return "in_progress"  # PR 없음

        state = pr_info.get("state", "")
        is_draft = pr_info.get("draft", False)

        if state == "MERGED":
            return "completed"
        elif state == "OPEN" and not is_draft:
            return "in_review"
        else:  # OPEN+draft, CLOSED, or unknown
            return "in_progress"

    sm = StateManager()
    data = sm._load()
    updated = []
    errors = []

    for project_name, project in data.get("projects", {}).items():
        if project.get("deleted_at"):
            continue

        repo = get_repo_from_path(project.get("repo_path", ""))
        if not repo:
            continue

        for task_name, task in project.get("tasks", {}).items():
            if task.get("archived_at"):
                continue

            branch = task.get("branch", "")
            if not branch:
                continue

            pr_info = get_pr_info(repo, branch)
            new_status = determine_status(pr_info)
            old_status = task.get("status", "pending")

            # PR 정보 저장
            task["pr"] = pr_info

            if new_status != old_status:
                task["status"] = new_status
                updated.append({
                    "project": project_name,
                    "task": task_name,
                    "old": old_status,
                    "new": new_status,
                    "pr": pr_info,
                })

    # PR 정보는 항상 저장 (상태 변경 없어도 PR 정보 업데이트 가능)
    sm._save(data)

    return {
        "success": True,
        "updated": updated,
        "count": len(updated)
    }


@app.get("/api/config")
async def get_config():
    """프론트엔드에 필요한 설정 반환"""
    return {"jira_url": settings.jira_url}


@app.get("/")
async def root():
    """API 상태"""
    return {"name": "Worktreee API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
