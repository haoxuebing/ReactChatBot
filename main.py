import json
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agentscope.model import OpenAIChatModel

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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True


async def sse_stream(messages: list[dict]) -> AsyncGenerator[str, None]:
    prev_text = ""
    stream = await model(messages)
    async for chunk in stream:
        for block in chunk.content:
            if block["type"] == "text":
                current_text = block["text"]
                delta = current_text[len(prev_text) :]
                if delta:
                    data = json.dumps(
                        {"choices": [{"delta": {"content": delta}}]},
                        ensure_ascii=False,
                    )
                    yield f"data: {data}\n\n"
                    prev_text = current_text

        if chunk.usage:
            data = json.dumps(
                {"choices": [{"delta": {"content": ""}}], "usage": _usage_to_dict(chunk.usage)},
                ensure_ascii=False,
            )
            yield f"data: {data}\n\n"

    yield "data: [DONE]\n\n"


def _usage_to_dict(usage) -> dict:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    messages = [m.model_dump() for m in request.messages]

    if not request.stream:
        full_text = ""
        stream = await model(messages)
        async for chunk in stream:
            for block in chunk.content:
                if block["type"] == "text":
                    full_text += block["text"]

        result = {
            "choices": [{"message": {"content": full_text, "role": "assistant"}}],
        }
        return result

    return StreamingResponse(
        sse_stream(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
