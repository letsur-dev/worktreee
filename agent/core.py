import json
from typing import Generator

from .llm import llm_client
from .tools import TOOLS, execute_tool


SYSTEM_PROMPT = """You are a Project Manager (PM) Agent that helps manage multiple projects across different machines.

Your capabilities:
- Register and manage projects (add_project, list_projects)
- Create tasks with git worktree and branches (create_task)
- Track task status and progress (get_status, update_task_status)
- Record progress reports (add_report)

When a user asks you to:
- "새 프로젝트 등록해줘" → use add_project tool
- "프로젝트 목록" → use list_projects tool
- "태스크 만들어줘" → use create_task tool
- "현황 보여줘" → use get_status tool
- "상태 업데이트" → use update_task_status tool
- "보고" → use add_report tool

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
        """스트리밍 응답을 위한 제너레이터"""
        # MVP에서는 non-streaming으로 처리 후 청크로 반환
        result = self.run(messages)
        # 한 번에 전체 응답 반환 (나중에 실제 스트리밍으로 개선 가능)
        yield result


# 싱글톤 인스턴스
pm_agent = PMAgent()
