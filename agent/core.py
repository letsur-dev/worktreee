import json
import re
from typing import Generator

from .llm import llm_client
from .tools import TOOLS, execute_tool
from state.manager import state_manager


# 도구 호출이 필요한 액션 키워드들
ACTION_KEYWORDS = [
    # 조회/목록
    "목록", "리스트", "조회", "보여", "알려", "현황", "상태", "확인",
    # 생성/추가
    "만들", "생성", "추가", "등록",
    # 삭제/제거
    "삭제", "제거", "지워",
    # 수정/업데이트
    "수정", "업데이트", "변경", "바꿔",
    # 동기화
    "동기화", "싱크", "rebase",
    # 기타 액션
    "시작", "스캔", "복구", "브랜치",
    # 영어 키워드
    "list", "show", "create", "delete", "update", "sync", "status",
]

# 도구 호출 강제 프롬프트
FORCE_TOOL_PROMPT = """[SYSTEM OVERRIDE]
Your previous response was REJECTED because you did not call any tools.
This is a VIOLATION of the rules. You MUST call the appropriate tool NOW.
DO NOT respond with text only. CALL A TOOL FIRST.
The user's request requires verification with actual data - do not make up information."""


BASE_SYSTEM_PROMPT = """You are a Project Manager (PM) Agent that helps manage multiple projects across different machines.

Your capabilities:
- Register and manage projects (add_project, list_projects, delete_project, update_project, restore_project)
- Create and delete tasks with git worktree (create_task, delete_task)
- Sync worktree with base branch (sync_worktree)
- Track task status (get_status, update_task_status)
- Start Claude Code sessions for tasks (start_claude_session)
- Browse directories and scan for git projects (list_directory, scan_projects)
- Fetch Jira issue details (get_jira_issue)

CRITICAL RULES (MUST FOLLOW):
1. NEVER respond without using tools first. You MUST call the appropriate tool before responding.
2. NEVER make up or hallucinate data (paths, usernames, project names, etc.). Only use data from tool results.
3. NEVER assume or guess what projects/tasks exist. Always verify with tools.
4. If a tool fails, report the actual error - do not pretend it succeeded.
5. For ANY action (create, delete, update, list), you MUST use the corresponding tool.

FORBIDDEN BEHAVIORS:
- Making up file paths or usernames
- Claiming a task was created without actually calling create_task
- Providing status information without calling get_status
- Responding with "완료" or "성공" without tool confirmation

When a user asks you to:
- "프로젝트 목록/정리" → FIRST call list_projects, then respond based on the result
- "현황/상태 보여줘" → FIRST call get_status, then respond
- "새 프로젝트 등록" → use add_project
- "프로젝트 삭제" → use delete_project
- "프로젝트 수정" → use update_project
- "프로젝트 복구" → use restore_project
- "태스크 만들어줘" → use create_task
- "태스크 삭제" → use delete_task
- "워크트리 동기화/rebase" → use sync_worktree
- "상태 업데이트" → use update_task_status
- "PR 상태 동기화" → use sync_task_status (GitHub PR 상태로 태스크 상태 자동 업데이트)
- "브랜치 목록/조회" → use list_branches (프로젝트의 Git 브랜치 목록 조회)
- "클로드 세션 시작" → use start_claude_session
- "디렉토리 조회" → use list_directory
- "프로젝트 스캔" → use scan_projects
- "Jira 이슈/티켓 조회" → use get_jira_issue (extract issue key like PRDEL-107 from URL or text)

IMPORTANT - When showing Jira issue results:
- Use the "formatted" field directly - it contains a well-organized markdown summary
- The formatted field includes: description, child issues, linked issues, comments, and attachments
- Just output the formatted content as-is, don't summarize or truncate it

Always respond in Korean unless the user speaks in English.
Be concise and helpful.
After using a tool, summarize the result naturally in conversation."""


def build_system_prompt() -> str:
    """프로젝트 목록을 포함한 동적 시스템 프롬프트 생성"""
    projects = state_manager.list_projects()

    if not projects:
        project_info = "현재 등록된 프로젝트가 없습니다."
    else:
        lines = []
        for p in projects:
            lines.append(f"- {p['name']}: {p['repo_path']} (machine: {p['machine']}, tasks: {p['task_count']})")
        project_info = "\n".join(lines)

    return f"""{BASE_SYSTEM_PROMPT}

=== CURRENT REGISTERED PROJECTS ===
{project_info}

IMPORTANT: Use ONLY the project names and paths listed above. Do NOT make up or guess paths."""


class PMAgent:
    def __init__(self):
        self.max_iterations = 10  # 무한 루프 방지
        self.max_force_retries = 2  # 도구 호출 강제 재시도 횟수

    def _requires_tool_call(self, messages: list[dict]) -> bool:
        """사용자 메시지가 도구 호출이 필요한 액션인지 확인"""
        # 마지막 사용자 메시지 확인
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                for keyword in ACTION_KEYWORDS:
                    if keyword in content:
                        return True
                break
        return False

    def run(self, messages: list[dict]) -> str:
        """메시지를 받아 처리하고 최종 응답을 반환"""
        # 동적 시스템 프롬프트 (프로젝트 목록 포함)
        system_prompt = build_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        requires_tool = self._requires_tool_call(messages)
        tool_was_called = False
        force_retry_count = 0

        for _ in range(self.max_iterations):
            response = llm_client.chat(full_messages, tools=TOOLS)
            choice = response.choices[0]
            message = choice.message

            # 도구 호출이 없으면 최종 응답
            if not message.tool_calls:
                # 할루시네이션 방지: 도구 호출이 필요한데 한번도 호출 안했으면 재시도
                if requires_tool and not tool_was_called and force_retry_count < self.max_force_retries:
                    force_retry_count += 1
                    # 강제 재시도 프롬프트 추가
                    full_messages.append({"role": "assistant", "content": message.content or ""})
                    full_messages.append({"role": "user", "content": FORCE_TOOL_PROMPT})
                    continue
                return message.content or ""

            # 도구 호출 처리 - 할루시네이션 방지 플래그 설정
            tool_was_called = True
            assistant_msg = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
            if message.content:
                assistant_msg["content"] = message.content
            full_messages.append(assistant_msg)

            # 각 도구 실행
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                args_str = tool_call.function.arguments or "{}"
                func_args = json.loads(args_str) if args_str.strip() else {}
                result = execute_tool(func_name, func_args)

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return "죄송합니다. 최대 반복 횟수를 초과했습니다."

    def run_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """스트리밍 응답을 위한 제너레이터 - 진행 상황 실시간 표시"""
        # 동적 시스템 프롬프트 (프로젝트 목록 포함)
        system_prompt = build_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        requires_tool = self._requires_tool_call(messages)
        tool_was_called = False
        force_retry_count = 0

        yield "🤔 요청 분석 중...\n\n"

        for iteration in range(self.max_iterations):
            response = llm_client.chat(full_messages, tools=TOOLS)
            choice = response.choices[0]
            message = choice.message

            # 도구 호출이 없으면 최종 응답
            if not message.tool_calls:
                # 할루시네이션 방지: 도구 호출이 필요한데 한번도 호출 안했으면 재시도
                if requires_tool and not tool_was_called and force_retry_count < self.max_force_retries:
                    force_retry_count += 1
                    yield "⚠️ 도구 호출 없이 응답 시도됨, 재시도 중...\n\n"
                    full_messages.append({"role": "assistant", "content": message.content or ""})
                    full_messages.append({"role": "user", "content": FORCE_TOOL_PROMPT})
                    continue
                yield "---\n\n"
                # 최종 응답을 청크로 나눠서 전송 (더 자연스러운 스트리밍)
                content = message.content or ""
                yield content
                return

            # 도구 호출 처리 - 할루시네이션 방지 플래그 설정
            tool_was_called = True
            assistant_msg = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
            if message.content:
                assistant_msg["content"] = message.content
            full_messages.append(assistant_msg)

            # 각 도구 실행 (진행 상황 표시)
            # 중요: 도구 실행을 먼저 완료한 후 yield (연결 끊김 방지)
            tool_results = []
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                args_str = tool_call.function.arguments or "{}"
                func_args = json.loads(args_str) if args_str.strip() else {}

                # 도구 실행 (yield 전에 먼저 실행!)
                args_preview = self._format_args_preview(func_args)
                result = execute_tool(func_name, func_args)
                result_preview = self._format_result_preview(result)

                tool_results.append({
                    "tool_call": tool_call,
                    "func_name": func_name,
                    "args_preview": args_preview,
                    "result": result,
                    "result_preview": result_preview,
                })

            # 도구 실행 완료 후 결과 yield (안전)
            for tr in tool_results:
                yield f"🔄 `{tr['func_name']}` {tr['args_preview']}\n"
                yield f"✅ {tr['result_preview']}\n\n"

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call"].id,
                    "content": tr["result"],
                })

        yield "⚠️ 최대 반복 횟수를 초과했습니다."

    def _format_args_preview(self, args: dict) -> str:
        """도구 인자 미리보기 포맷"""
        if not args:
            return ""
        # 주요 인자만 표시
        key_args = []
        for key in ["project", "task_name", "name", "issue_key", "path"]:
            if key in args:
                key_args.append(f"{key}={args[key]}")
        if key_args:
            return f"({', '.join(key_args)})"
        return ""

    def _format_result_preview(self, result: str) -> str:
        """도구 결과 미리보기 포맷"""
        try:
            data = json.loads(result)
            if "error" in data:
                return f"❌ 오류: {data['error'][:50]}..."
            if "success" in data and data["success"]:
                # 성공 케이스별 메시지
                if "projects" in data:
                    return f"프로젝트 {len(data['projects'])}개 조회됨"
                if "worktree" in data:
                    return f"워크트리 생성: {data['worktree'].split('/')[-1]}"
                if "claude_session" in data:
                    return "Claude 세션 시작됨"
                if "deleted_task" in data:
                    return f"태스크 삭제됨: {data['deleted_task']}"
                if "synced" in data:
                    return f"PR 상태 동기화: {data['changed']}개 변경됨"
                return "완료"
            if isinstance(data, dict):
                if "key" in data:  # Jira issue
                    return f"Jira: {data.get('key')} - {data.get('summary', '')[:30]}"
                if "projects" in data:
                    count = len(data["projects"])
                    return f"프로젝트 {count}개 조회됨"
                if "directories" in data or "files" in data:
                    return "디렉토리 조회됨"
                if "branches" in data:
                    return f"브랜치 {data['count']}개 조회됨"
            return "완료"
        except:
            return "완료"


# 싱글톤 인스턴스
pm_agent = PMAgent()
