import json
import os
import time
import uuid
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from agentscope.model import OpenAIChatModel
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg

load_dotenv()

app = FastAPI(title="AgentScope Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = OpenAIChatModel(
    model_name=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    stream=True,
    client_kwargs={
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    },
)

sessions: dict[str, InMemoryMemory] = {}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True
    session_id: str = ""


def get_or_create_session(session_id: str) -> tuple[str, InMemoryMemory]:
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]
    new_id = session_id or uuid.uuid4().hex[:12]
    memory = InMemoryMemory()
    sessions[new_id] = memory
    return new_id, memory


def msg_to_openai_dict(msg: Msg) -> dict:
    return {"role": msg.role, "content": msg.content}


async def build_messages_with_history(
    memory: InMemoryMemory,
    new_messages: list[dict],
) -> list[dict]:
    history = await memory.get_memory()
    result = []
    for h in history:
        result.append(msg_to_openai_dict(h))
    result.extend(new_messages)
    return result


async def save_to_memory(
    memory: InMemoryMemory,
    user_messages: list[dict],
    assistant_content: str,
) -> None:
    history_msgs = [
        Msg(name=msg["role"], role=msg["role"], content=msg["content"])
        for msg in user_messages
    ]
    history_msgs.append(
        Msg(
            name="assistant",
            role="assistant",
            content=assistant_content,
        ),
    )
    await memory.add(history_msgs)


def _make_sse_chunk(
    chunk_id: str | None,
    session_id: str,
    delta_content: str,
    finish_reason: str | None = None,
    usage: dict | None = None,
) -> str:
    choice: dict[str, object] = {
        "index": 0,
        "delta": {"content": delta_content},
        "finish_reason": finish_reason,
    }
    payload: dict[str, object] = {
        "id": chunk_id,
        "session_id": session_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model.model_name,
        "choices": [choice],
    }
    if usage:
        payload["usage"] = usage
    return json.dumps(payload, ensure_ascii=False)


async def sse_stream(
    messages: list[dict],
    session_id: str,
    memory: InMemoryMemory | None = None,
    user_messages: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    prev_text = ""
    full_text = ""
    chunk_id = None
    has_content = False

    stream = await model(messages)
    async for chunk in stream:
        if chunk_id is None:
            chunk_id = getattr(chunk, "id", None)

        for block in chunk.content:
            if block["type"] == "text":
                current_text = block["text"]
                delta = current_text[len(prev_text):]
                if delta:
                    has_content = True
                    yield f"data: {_make_sse_chunk(chunk_id, session_id, delta)}\n\n"
                    prev_text = current_text
                    full_text = current_text

        if chunk.usage:
            usage = _usage_to_dict(chunk.usage)
            yield f"data: {_make_sse_chunk(chunk_id, session_id, '', usage=usage)}\n\n"

    if has_content:
        yield f"data: {_make_sse_chunk(chunk_id, session_id, '', finish_reason='stop')}\n\n"

    yield "data: [DONE]\n\n"

    if memory is not None and user_messages is not None and full_text:
        await save_to_memory(memory, user_messages, full_text)


def _usage_to_dict(usage) -> dict:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    messages_raw = [m.model_dump() for m in request.messages]
    session_id, memory = get_or_create_session(request.session_id)

    system_prompts = [m for m in messages_raw if m["role"] == "system"]
    user_assistant_messages = [m for m in messages_raw if m["role"] != "system"]

    full_messages = await build_messages_with_history(memory, user_assistant_messages)
    if system_prompts:
        full_messages = system_prompts + full_messages

    if not request.stream:
        full_text = ""
        final_usage = None
        first_chunk_id = None
        stream = await model(full_messages)
        async for chunk in stream:
            if first_chunk_id is None:
                first_chunk_id = getattr(chunk, "id", None)
            for block in chunk.content:
                if block["type"] == "text":
                    full_text = block["text"]
            if chunk.usage:
                final_usage = chunk.usage

        await save_to_memory(memory, user_assistant_messages, full_text)

        return JSONResponse(
            content={
                "session_id": session_id,
                "id": first_chunk_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model.model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": full_text,
                        },
                        "finish_reason": "stop",
                    },
                ],
                "usage": _usage_to_dict(final_usage) if final_usage else None,
            },
            headers={"X-Session-Id": session_id},
        )

    return StreamingResponse(
        sse_stream(
            full_messages,
            session_id,
            memory=memory,
            user_messages=user_assistant_messages,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )
