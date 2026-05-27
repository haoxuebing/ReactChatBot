import json
import os
import time
import logging
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from agentscope.model import OpenAIChatModel

from agents import ReActAgent
from memory import MemoryManager
from schemas import ChatRequest

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(title="AgentScope Chat API", version="2.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化核心组件
model = OpenAIChatModel(
    model_name=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    stream=True,
    client_kwargs={
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    },
)

memory_manager = MemoryManager()
agent = ReActAgent(model)


def _make_sse_chunk(
    chunk_id: str | None,
    session_id: str,
    delta_content: str,
    finish_reason: str | None = None,
    tool_calls: list | None = None,
) -> str:
    """生成SSE数据块"""
    choice: dict[str, object] = {
        "index": 0,
        "delta": {"content": delta_content} if delta_content else {},
        "finish_reason": finish_reason,
    }
    if tool_calls:
        choice["tool_calls"] = tool_calls
    
    payload: dict[str, object] = {
        "id": chunk_id,
        "session_id": session_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model.model_name,
        "choices": [choice],
    }
    return json.dumps(payload, ensure_ascii=False)


async def sse_stream_wrapper(
    agent_stream: AsyncGenerator[dict, None],
    session_id: str,
) -> AsyncGenerator[str, None]:
    """SSE流包装器"""
    async for chunk in agent_stream:
        chunk_id = chunk.get("id")
        delta_content = chunk["choices"][0]["delta"].get("content", "")
        finish_reason = chunk["choices"][0]["finish_reason"]
        tool_calls = chunk["choices"][0].get("tool_calls")
        
        yield f"data: {_make_sse_chunk(chunk_id, session_id, delta_content, finish_reason, tool_calls)}\n\n"
    
    yield "data: [DONE]\n\n"


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """智能体聊天接口（V2）"""
    # 获取或创建会话
    session_id, memory_backend = memory_manager.get_or_create_session(request.session_id)
    
    # 提取消息
    messages_raw = [m.model_dump() for m in request.messages]
    system_prompts = [m for m in messages_raw if m["role"] == "system"]
    user_assistant_messages = [m for m in messages_raw if m["role"] != "system"]
    
    # 构建包含历史的完整消息
    full_messages = await memory_manager.build_messages_with_history(
        memory_backend, user_assistant_messages
    )
    if system_prompts:
        full_messages = system_prompts + full_messages
    
    # 打印请求日志
    logger.info(f"[API/CHAT] Session: {session_id}, Stream: {request.stream}, Messages: {len(full_messages)}")
    if user_assistant_messages:
        logger.info(f"[API/CHAT] User Message: {user_assistant_messages[-1]['content'][:100]}...")
    
    # 调用智能体
    if not request.stream:
        # 非流式响应
        result = await agent.chat(full_messages, memory_backend, stream=False)
        
        # 保存到记忆
        if result["choices"][0]["message"]["content"]:
            await memory_manager.save_to_memory(
                memory_backend,
                user_assistant_messages,
                result["choices"][0]["message"]["content"]
            )
        
        # 添加session_id到响应
        result["session_id"] = session_id
        result["created"] = int(time.time())
        
        # 打印响应日志
        response_content = result["choices"][0]["message"]["content"]
        logger.info(f"[API/CHAT] Response (non-stream): {response_content[:200]}...")
        
        return JSONResponse(
            content=result,
            headers={"X-Session-Id": session_id},
        )
    
    # 流式响应
    async def streaming_response():
        full_text = ""
        chunk_count = 0
        async for chunk in await agent.chat(full_messages, memory_backend, stream=True):
            content = chunk["choices"][0]["delta"].get("content", "")
            if content:
                full_text += content
                chunk_count += 1
                # 每5个chunk或内容超过100字符打印一次日志
                if chunk_count % 5 == 0 or len(full_text) > 100:
                    logger.info(f"[API/CHAT] Stream chunk #{chunk_count}, Total length: {len(full_text)}")
                    chunk_count = 0
            yield f"data: {_make_sse_chunk(chunk.get('id'), session_id, content, chunk['choices'][0]['finish_reason'])}\n\n"
        
        # 保存到记忆
        if full_text:
            await memory_manager.save_to_memory(
                memory_backend,
                user_assistant_messages,
                full_text
            )
        
        # 打印完整响应日志
        logger.info(f"[API/CHAT] Stream completed. Total response: {full_text[:200]}...")
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        streaming_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )


@app.get("/api/tools")
async def list_tools():
    """获取可用工具列表"""
    return {"tools": agent.tools}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    # 由于当前使用InMemoryBackend，无法直接删除，这里只是演示
    return {"message": f"Session {session_id} deleted"}

@app.get("/api/sessions")
async def list_sessions():
    """获取所有会话"""
    return {"sessions": memory_manager.list_sessions()}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """获取指定会话"""
    result = await memory_manager.get_session(session_id)
    return {"session": result}

@app.get("/")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "2.0", "model": model.model_name}
