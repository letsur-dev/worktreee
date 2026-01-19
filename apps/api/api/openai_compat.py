import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.core import pm_agent


router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "pm-agent"
    messages: list[Message]
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int | None = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


@router.get("/v1/models")
async def list_models() -> ModelsResponse:
    return ModelsResponse(
        data=[
            ModelInfo(
                id="pm-agent",
                created=int(time.time()),
                owned_by="local",
            )
        ]
    )


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    if request.stream:
        return StreamingResponse(
            stream_response(messages),
            media_type="text/event-stream",
        )

    # Non-streaming 응답
    response_content = pm_agent.run(messages)

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(time.time()),
        model="pm-agent",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=Message(role="assistant", content=response_content),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=0,  # 실제 계산은 생략
            completion_tokens=0,
            total_tokens=0,
        ),
    )


async def stream_response(messages: list[dict]) -> AsyncGenerator[str, None]:
    """SSE 스트리밍 응답 생성"""
    response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())

    # PM Agent 실행
    for chunk in pm_agent.run_stream(messages):
        data = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": "pm-agent",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": chunk},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(data)}\n\n"

    # 종료 청크
    final_data = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": "pm-agent",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    yield f"data: {json.dumps(final_data)}\n\n"
    yield "data: [DONE]\n\n"
