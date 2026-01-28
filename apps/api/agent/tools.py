import json
import subprocess
from typing import Any

from state.manager import state_manager


# OpenAI 함수 스키마 형식
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_project",
            "description": "새 프로젝트를 등록합니다. Git 레포지토리 경로와 실행할 머신을 지정합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "프로젝트 이름 (고유 식별자)",
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "Git 레포지토리 절대 경로",
                    },
                    "machine": {
                        "type": "string",
                        "description": "실행 머신 (local, mac, nuc)",
                        "default": "local",
                    },
                },
                "required": ["name", "repo_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "등록된 모든 프로젝트 목록을 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_project",
            "description": "프로젝트를 삭제합니다. 기본은 soft delete (복구 가능).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "삭제할 프로젝트 이름",
                    },
                    "hard": {
                        "type": "boolean",
                        "description": "true면 완전 삭제 (복구 불가)",
                        "default": False,
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restore_project",
            "description": "삭제된 프로젝트를 복구합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "복구할 프로젝트 이름",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_project",
            "description": "프로젝트 정보를 수정합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "수정할 프로젝트 이름",
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "새 Git 레포지토리 경로",
                    },
                    "machine": {
                        "type": "string",
                        "description": "새 실행 머신 (local, mac 등)",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "프로젝트 또는 전체 현황을 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름 (없으면 전체 현황)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "프로젝트에 새 태스크를 생성합니다. Git worktree와 branch를 자동으로 생성합니다. Jira 티켓이나 Notion 문서를 연결할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "태스크 이름 (워크트리 폴더명으로 사용, 예: PRDEL-107-invite-feature)",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Git 브랜치명 (예: feature/PRDEL-107/invite-feature). 생략하면 task_name 사용",
                    },
                    "context": {
                        "type": "string",
                        "description": "태스크 컨텍스트 (목표, 제약사항 등)",
                    },
                    "jira_key": {
                        "type": "string",
                        "description": "연결할 Jira 이슈 키 (예: PRDEL-107)",
                    },
                    "notion_urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "연결할 Notion 문서 URL 목록",
                    },
                },
                "required": ["project", "task_name", "context"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_context",
            "description": "태스크의 전체 컨텍스트를 가져옵니다. 연결된 Jira 이슈와 Notion 문서 내용을 함께 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "태스크 이름",
                    },
                },
                "required": ["project", "task_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "태스크를 삭제합니다. 연결된 워크트리도 함께 정리됩니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "삭제할 태스크 이름",
                    },
                    "cleanup_worktree": {
                        "type": "boolean",
                        "description": "워크트리도 함께 삭제할지 여부 (기본: true)",
                        "default": True,
                    },
                },
                "required": ["project", "task_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task_status",
            "description": "태스크 상태를 업데이트합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "태스크 이름",
                    },
                    "status": {
                        "type": "string",
                        "description": "새 상태 (pending, in_progress, in_review, completed)",
                        "enum": ["pending", "in_progress", "in_review", "completed"],
                    },
                },
                "required": ["project", "task_name", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_worktree",
            "description": "기존 태스크에 Git worktree를 생성합니다. 태스크 생성시 자동으로 호출되지만, 수동으로도 호출 가능합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "태스크 이름",
                    },
                },
                "required": ["project", "task_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sync_worktree",
            "description": "워크트리를 최신 base 브랜치 기준으로 rebase합니다. 충돌 발생시 abort하고 알려줍니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "태스크 이름",
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "rebase 기준 브랜치 (기본: develop)",
                    },
                },
                "required": ["project", "task_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_claude_session",
            "description": "태스크용 Claude Code 세션을 시작합니다. 레포를 분석하고 태스크 컨텍스트를 이해한 후, 사용자가 'claude --continue'로 이어서 작업할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "태스크 이름",
                    },
                },
                "required": ["project", "task_name"],
            },
        },
    },
    # 통합 도구 (로컬/원격 공통, Documents 기준)
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Documents 하위 디렉토리 내용을 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Documents 기준 상대경로 (예: 'letsur'). 생략하면 Documents 루트.",
                    },
                    "host": {
                        "type": "string",
                        "description": "'mac'이면 원격 Mac, 생략하면 로컬(NUC).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_projects",
            "description": "Documents 하위를 스캔하여 Git 프로젝트를 찾습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Documents 기준 상대경로 (예: 'letsur'). 생략하면 전체 스캔.",
                    },
                    "host": {
                        "type": "string",
                        "description": "'mac'이면 원격 Mac, 생략하면 로컬(NUC).",
                    },
                },
            },
        },
    },
    # Jira 연동
    {
        "type": "function",
        "function": {
            "name": "get_jira_issue",
            "description": "Jira 이슈 정보를 조회합니다. 이슈 키(예: PRDEL-107)를 입력하면 제목, 설명, 상태, 담당자 등을 반환합니다. recursive=true로 하면 하위의 하위, 링크된 이슈까지 전체 트리를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira 이슈 키 (예: PRDEL-107, PROJ-123)",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "true면 하위의 하위, 링크된 이슈까지 재귀적으로 전체 트리 조회 (기본값: false)",
                    },
                    "fetch_notion": {
                        "type": "boolean",
                        "description": "true면 Notion 링크 발견시 자동으로 내용 조회 (기본값: true)",
                    },
                },
                "required": ["issue_key"],
            },
        },
    },
    # Jira 다중 이슈 병렬 조회
    {
        "type": "function",
        "function": {
            "name": "get_jira_issues_batch",
            "description": "여러 Jira 이슈를 병렬로 한번에 조회합니다. 상위 이슈의 하위 이슈들을 한번에 조회할 때 유용합니다. 각 이슈의 설명, 댓글, 상태 등을 모두 포함합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Jira 이슈 키 목록 (예: [\"PRDEL-101\", \"PRDEL-102\", \"PRDEL-103\"])",
                    },
                },
                "required": ["issue_keys"],
            },
        },
    },
    # Jira 그래프 시각화
    {
        "type": "function",
        "function": {
            "name": "get_jira_graph",
            "description": "Jira 이슈와 하위 이슈들을 Mermaid 다이어그램으로 시각화합니다. 상태별 이모지와 링크 관계를 포함한 전체 트리를 그래프로 보여줍니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira 이슈 키 (예: PRDEL-85)",
                    },
                },
                "required": ["issue_key"],
            },
        },
    },
    # Jira 그래프 시각화 (HTML/D3.js)
    {
        "type": "function",
        "function": {
            "name": "get_jira_graph_html",
            "description": "Jira 이슈 관계를 D3.js 인터랙티브 그래프로 시각화합니다. 드래그, 줌, 클릭(Jira/Notion 이동) 가능한 HTML 파일을 생성합니다. Reflect App 스타일의 네트워크 그래프이며, 연결된 Notion 문서도 표시합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira 이슈 키 (예: PRDEL-85)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "HTML 파일 저장 경로 (옵션, 미지정시 data/jira_graphs/에 저장)",
                    },
                    "include_notion": {
                        "type": "boolean",
                        "description": "Notion 문서를 그래프에 포함할지 여부 (기본값: true)",
                    },
                },
                "required": ["issue_key"],
            },
        },
    },
    # Jira 이미지 분석
    {
        "type": "function",
        "function": {
            "name": "analyze_jira_image",
            "description": "Jira 이슈에 첨부된 이미지를 분석합니다. 스크린샷, 다이어그램, 목업 등을 AI가 분석하여 설명합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira 이슈 키 (예: PRDEL-102)",
                    },
                    "attachment_index": {
                        "type": "integer",
                        "description": "분석할 이미지 인덱스 (0부터 시작, 기본값: 0)",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "이미지에 대해 물어볼 질문 (기본값: '이 이미지를 분석해주세요.')",
                    },
                },
                "required": ["issue_key"],
            },
        },
    },
    # PR 상태 동기화
    {
        "type": "function",
        "function": {
            "name": "sync_task_status",
            "description": "GitHub PR 상태를 확인하여 태스크 상태를 자동 동기화합니다. PR이 OPEN이면 in_review, MERGED면 completed로 변경합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "태스크 이름 (생략하면 프로젝트의 모든 태스크 동기화)",
                    },
                },
                "required": ["project"],
            },
        },
    },
    # 브랜치 목록 조회
    {
        "type": "function",
        "function": {
            "name": "list_branches",
            "description": "프로젝트의 Git 브랜치 목록을 조회합니다. 로컬 및 리모트 브랜치를 모두 표시합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "브랜치 이름 필터 패턴 (예: feature/, fix/)",
                    },
                    "remote_only": {
                        "type": "boolean",
                        "description": "리모트 브랜치만 조회 (기본: false)",
                        "default": False,
                    },
                },
                "required": ["project"],
            },
        },
    },
    # GitHub PR 목록 조회
    {
        "type": "function",
        "function": {
            "name": "list_open_prs",
            "description": "프로젝트의 열린 GitHub PR 목록을 조회합니다. PR 번호, 제목, 브랜치명, 작성자 등을 확인할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "author": {
                        "type": "string",
                        "description": "작성자로 필터링 (선택, 예: @me)",
                    },
                },
                "required": ["project"],
            },
        },
    },
    # Notion 연동
    {
        "type": "function",
        "function": {
            "name": "get_notion_page",
            "description": "Notion 페이지 내용을 가져옵니다. Jira 이슈에 링크된 Notion 페이지를 읽을 때 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_url_or_id": {
                        "type": "string",
                        "description": "Notion 페이지 URL 또는 ID (예: https://notion.so/workspace/Page-Title-abc123)",
                    },
                },
                "required": ["page_url_or_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_notion",
            "description": "Notion 워크스페이스에서 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색어",
                    },
                    "page_url": {
                        "type": "string",
                        "description": "특정 페이지 내에서만 검색 (선택)",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """도구를 실행하고 결과를 JSON 문자열로 반환"""
    try:
        if name == "add_project":
            result = state_manager.add_project(
                name=arguments["name"],
                repo_path=arguments["repo_path"],
                machine=arguments.get("machine", "local"),
            )
        elif name == "list_projects":
            result = state_manager.list_projects()
        elif name == "delete_project":
            result = state_manager.delete_project(
                name=arguments["name"],
                hard=arguments.get("hard", False),
            )
        elif name == "restore_project":
            result = state_manager.restore_project(name=arguments["name"])
        elif name == "update_project":
            result = state_manager.update_project(
                name=arguments["name"],
                repo_path=arguments.get("repo_path"),
                machine=arguments.get("machine"),
            )
        elif name == "get_status":
            result = state_manager.get_status(project=arguments.get("project"))
        elif name == "create_task":
            # 먼저 태스크 등록
            result = state_manager.add_task(
                project=arguments["project"],
                task_name=arguments["task_name"],
                context=arguments["context"],
                branch=arguments.get("branch"),  # 브랜치명 (없으면 task_name 사용)
                jira_key=arguments.get("jira_key"),
                notion_urls=arguments.get("notion_urls"),
            )
            # Phase 2: 워크트리 자동 생성
            if result.get("success"):
                worktree_result = state_manager.create_worktree(
                    project=arguments["project"],
                    task_name=arguments["task_name"],
                )
                # 워크트리 생성 결과를 응답에 병합
                if worktree_result.get("success"):
                    result["worktree"] = worktree_result["worktree"]
                    result["branch"] = worktree_result["branch"]

                    # Phase 3: Claude 세션 자동 시작
                    claude_result = state_manager.start_claude_session(
                        project=arguments["project"],
                        task_name=arguments["task_name"],
                    )
                    if claude_result.get("success"):
                        result["claude_session"] = "started"
                        result["continue_command"] = "claude --continue"
                    else:
                        result["claude_session_error"] = claude_result.get("error")
                else:
                    result["worktree_error"] = worktree_result.get("error")
        elif name == "create_worktree":
            result = state_manager.create_worktree(
                project=arguments["project"],
                task_name=arguments["task_name"],
            )
        elif name == "sync_worktree":
            result = state_manager.sync_worktree(
                project=arguments["project"],
                task_name=arguments["task_name"],
                base_branch=arguments.get("base_branch", "develop"),
            )
        elif name == "start_claude_session":
            result = state_manager.start_claude_session(
                project=arguments["project"],
                task_name=arguments["task_name"],
            )
        elif name == "get_task_context":
            result = state_manager.get_task_context(
                project=arguments["project"],
                task_name=arguments["task_name"],
            )
        elif name == "delete_task":
            result = state_manager.delete_task(
                project=arguments["project"],
                task_name=arguments["task_name"],
                cleanup_worktree=arguments.get("cleanup_worktree", True),
            )
        elif name == "update_task_status":
            result = state_manager.update_task_status(
                project=arguments["project"],
                task_name=arguments["task_name"],
                status=arguments["status"],
            )
        # 통합 도구 (로컬/원격 공통, Documents 기준)
        elif name == "list_directory":
            result = state_manager.list_directory(
                path=arguments.get("path", ""),
                host=arguments.get("host"),
            )
        elif name == "scan_projects":
            result = state_manager.scan_projects(
                path=arguments.get("path", ""),
                host=arguments.get("host"),
            )
        elif name == "get_jira_issue":
            result = state_manager.get_jira_issue(
                issue_key=arguments["issue_key"],
                recursive=arguments.get("recursive", False),
                fetch_notion=arguments.get("fetch_notion", True),
            )
        elif name == "get_jira_issues_batch":
            result = state_manager.get_jira_issues_batch(
                issue_keys=arguments["issue_keys"],
            )
        elif name == "get_jira_graph":
            result = state_manager.get_jira_graph(
                issue_key=arguments["issue_key"],
            )
        elif name == "get_jira_graph_html":
            result = state_manager.get_jira_graph_html(
                issue_key=arguments["issue_key"],
                output_path=arguments.get("output_path"),
            )
        elif name == "analyze_jira_image":
            result = state_manager.analyze_jira_image(
                issue_key=arguments["issue_key"],
                attachment_index=arguments.get("attachment_index", 0),
                prompt=arguments.get("prompt", "이 이미지를 분석해주세요."),
            )
        elif name == "sync_task_status":
            result = state_manager.sync_task_status(
                project=arguments["project"],
                task_name=arguments.get("task_name"),
            )
        elif name == "list_branches":
            result = state_manager.list_branches(
                project=arguments["project"],
                pattern=arguments.get("pattern"),
                remote_only=arguments.get("remote_only", False),
            )
        # Notion 도구
        elif name == "get_notion_page":
            result = state_manager.get_notion_page(
                page_url_or_id=arguments["page_url_or_id"],
            )
        elif name == "search_notion":
            result = state_manager.search_notion(
                query=arguments["query"],
                page_url=arguments.get("page_url"),
            )
        # GitHub PR 도구
        elif name == "list_open_prs":
            result = state_manager.list_open_prs(
                project=arguments["project"],
                author=arguments.get("author"),
            )
        else:
            result = {"error": f"알 수 없는 도구: {name}"}

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
