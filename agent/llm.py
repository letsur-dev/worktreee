from openai import OpenAI

from config import settings


class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
        )
        self.model = settings.openai_model

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
    ):
        """LLM에 채팅 요청을 보냅니다."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self.client.chat.completions.create(**kwargs)


# 싱글톤 인스턴스
llm_client = LLMClient()
