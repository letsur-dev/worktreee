import json
from typing import Generator

from .llm import llm_client
from .tools import TOOLS, execute_tool


SYSTEM_PROMPT = """You are a Project Manager (PM) Agent that helps manage multiple projects across different machines.

Your capabilities:
- Register and manage projects (add_project, list_projects, delete_project, update_project, restore_project)
- Create and delete tasks with git worktree (create_task, delete_task)
- Sync worktree with base branch (sync_worktree)
- Track task status (get_status, update_task_status)
- Start Claude Code sessions for tasks (start_claude_session)
- Browse directories and scan for git projects (list_directory, scan_projects)
- Fetch Jira issue details (get_jira_issue)

IMPORTANT RULES:
1. ALWAYS use tools to get current data. NEVER rely on your memory or previous conversation context.
2. When asked about projects, tasks, or status → ALWAYS call the appropriate tool first (list_projects, get_status, etc.)
3. Do not assume or guess what projects/tasks exist. Always verify with tools.

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

Always respond in Korean unless the user speaks in English.
Be concise and helpful.
After using a tool, summarize the result naturally in conversation."""


class PMAgent:
    def __init__(self):
        self.max_iterations = 10  # 무한 루프 방지

    def run(self, messages: list[dict]) -> str:
        """메시지를 받아 처리하고 최종 응답을 반환"""
        # 시스템 프롬프트 추가
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        for _ in range(self.max_iterations):
            response = llm_client.chat(full_messages, tools=TOOLS)
            choice = response.choices[0]
            message = choice.message

            # 도구 호출이 없으면 최종 응답
            if not message.tool_calls:
                return message.content or ""

            # 도구 호출 처리
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
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        yield "🤔 요청 분석 중...\n\n"

        for iteration in range(self.max_iterations):
            response = llm_client.chat(full_messages, tools=TOOLS)
            choice = response.choices[0]
            message = choice.message

            # 도구 호출이 없으면 최종 응답
            if not message.tool_calls:
                yield "---\n\n"
                # 최종 응답을 청크로 나눠서 전송 (더 자연스러운 스트리밍)
                content = message.content or ""
                yield content
                return

            # 도구 호출 처리
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
