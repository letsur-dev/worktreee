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
            "description": "프로젝트에 새 태스크를 생성합니다. Git worktree와 branch를 자동으로 생성합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "프로젝트 이름",
                    },
                    "task_name": {
                        "type": "string",
                        "description": "태스크 이름 (branch 이름으로도 사용)",
                    },
                    "context": {
                        "type": "string",
                        "description": "태스크 컨텍스트 (목표, 제약사항 등)",
                    },
                },
                "required": ["project", "task_name", "context"],
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
                        "description": "새 상태 (pending, in_progress, completed)",
                        "enum": ["pending", "in_progress", "completed"],
                    },
                },
                "required": ["project", "task_name", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_report",
            "description": "태스크에 진행 보고를 추가합니다.",
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
                    "content": {
                        "type": "string",
                        "description": "보고 내용",
                    },
                },
                "required": ["project", "task_name", "content"],
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
        elif name == "get_status":
            result = state_manager.get_status(project=arguments.get("project"))
        elif name == "create_task":
            # 먼저 태스크 등록
            result = state_manager.add_task(
                project=arguments["project"],
                task_name=arguments["task_name"],
                context=arguments["context"],
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
                else:
                    result["worktree_error"] = worktree_result.get("error")
        elif name == "create_worktree":
            result = state_manager.create_worktree(
                project=arguments["project"],
                task_name=arguments["task_name"],
            )
        elif name == "update_task_status":
            result = state_manager.update_task_status(
                project=arguments["project"],
                task_name=arguments["task_name"],
                status=arguments["status"],
            )
        elif name == "add_report":
            result = state_manager.add_report(
                project=arguments["project"],
                task_name=arguments["task_name"],
                content=arguments["content"],
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
        else:
            result = {"error": f"알 수 없는 도구: {name}"}

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
