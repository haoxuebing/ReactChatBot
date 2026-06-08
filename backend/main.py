import json
import os
import time
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

from agentscope.credential import OpenAICredential
from agentscope.model import OpenAIChatModel

from agents import ReActAgent
from http_utils import get_client_ip
from memory import MemoryManager
from schemas import ChatRequest, UsernameRequest, CreateSessionRequest
from tools import build_toolkit, build_mcp_clients, verify_mcp_clients

# 加载环境变量
load_dotenv()

agent: ReActAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    try:
        mcp_clients = build_mcp_clients()
        mcp_summary = await verify_mcp_clients(mcp_clients)
        healthy_clients = [
            client for client in mcp_clients if mcp_summary.get(client.name)
        ]
        if len(healthy_clients) < len(mcp_clients):
            skipped = [c.name for c in mcp_clients if c not in healthy_clients]
            logger.warning("以下 MCP 服务不可用，已跳过注册: %s", skipped)
        toolkit = build_toolkit(mcp_clients=healthy_clients)
        agent = ReActAgent(model, toolkit=toolkit)
        tool_names = [s["function"]["name"] for s in await agent.list_tools_async()]
        logger.info("AgentScope 2.0 智能体已初始化，工具: %s", tool_names)
        if mcp_summary:
            logger.info("MCP 工具探测结果: %s", mcp_summary)
    except Exception:
        logger.exception("智能体初始化失败")
        raise
    yield


# 创建FastAPI应用（文档路径见 .env；设为空字符串可关闭对应页面）
app = FastAPI(
    title="AgentScope Chat API",
    version="2.0",
    lifespan=lifespan,
    docs_url=os.getenv("DOCS_URL", "/docs") or None,
    redoc_url=os.getenv("REDOC_URL", "/redoc") or None,
    openapi_url=os.getenv("OPENAPI_URL", "/openapi.json") or None,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id", "X-Client-Ip"],
)

# 初始化核心组件
model = OpenAIChatModel(
    credential=OpenAICredential(
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
    ),
    model=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
    stream=True,
)

memory_manager = MemoryManager(
    data_dir=os.getenv("MEMORY_DATA_DIR"),
)


def _get_agent() -> ReActAgent:
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent


def _make_sse_chunk(
    chunk_id: str | None,
    session_id: str,
    delta: dict,
    finish_reason: str | None = None,
) -> str:
    """生成SSE数据块"""
    choice: dict[str, object] = {
        "index": 0,
        "delta": delta,
        "finish_reason": finish_reason,
    }

    payload: dict[str, object] = {
        "id": chunk_id,
        "session_id": session_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model.model,
        "choices": [choice],
    }
    return json.dumps(payload, ensure_ascii=False)


@app.post("/api/chat")
async def chat(request: ChatRequest, http_request: Request):
    """智能体聊天接口（V2）"""
    chat_agent = _get_agent()

    # 获取或创建会话
    session_id, memory_backend = memory_manager.get_or_create_session(
        request.session_id,
        request.username or None,
    )
    client_ip = get_client_ip(http_request)

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
    logger.info(
        f"[API/CHAT] IP: {client_ip}, Session: {session_id}, Stream: {request.stream}, Messages: {len(full_messages)}"
    )
    if user_assistant_messages:
        logger.info(
            f"[API/CHAT] IP: {client_ip}, User Message: {user_assistant_messages[-1]['content'][:100]}..."
        )

    # 调用智能体
    if not request.stream:
        # 非流式响应
        result = await chat_agent.chat(full_messages, stream=False)

        # 保存到记忆
        if result["choices"][0]["message"]["content"]:
            await memory_manager.save_to_memory(
                memory_backend,
                user_assistant_messages,
                result["choices"][0]["message"]["content"],
                client_ip,
            )

        # 添加session_id到响应
        result["session_id"] = session_id
        result["created"] = int(time.time())

        # 打印响应日志
        response_content = result["choices"][0]["message"]["content"]
        logger.info(f"[API/CHAT] Response (non-stream): {response_content[:200]}...")

        return JSONResponse(
            content=result,
            headers={"X-Session-Id": session_id, "X-Client-Ip": client_ip},
        )

    # 流式响应
    async def streaming_response():
        full_text = ""
        chunk_count = 0
        try:
            async for chunk in await chat_agent.chat(full_messages, stream=True):
                choice = chunk["choices"][0]
                delta = choice.get("delta", {})
                content = delta.get("content", "")
                if content and not delta.get("content_reset"):
                    full_text += content
                    chunk_count += 1
                    if chunk_count % 5 == 0 or len(full_text) > 100:
                        chunk_count = 0
                yield f"data: {_make_sse_chunk(chunk.get('id'), session_id, delta, choice.get('finish_reason'))}\n\n"
        except Exception:
            logger.exception("[API/CHAT] Stream failed")
            if not full_text:
                full_text = "抱歉，处理请求时发生错误，请稍后重试。"
                yield f"data: {_make_sse_chunk(None, session_id, {'content': full_text}, 'stop')}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 保存到记忆
        if full_text and not full_text.strip().startswith("{"):
            await memory_manager.save_to_memory(
                memory_backend,
                user_assistant_messages,
                full_text,
                client_ip,
            )

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
            "X-Client-Ip": client_ip,
        },
    )


@app.get("/api/tools")
async def list_tools():
    """获取可用工具列表"""
    chat_agent = _get_agent()
    return {"tools": await chat_agent.list_tools_async()}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """软删除指定会话（数据保留，不再出现在列表中）"""
    if not memory_manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"message": f"Session {session_id} deleted"}


@app.post("/api/sessions")
async def create_session(
    request: CreateSessionRequest,
    http_request: Request,
):
    """创建并绑定用户会话"""
    try:
        session_id, _ = memory_manager.get_or_create_session(
            request.session_id or None,
            request.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "session_id": session_id,
        "username": request.username.strip()[:12],
    }


@app.get("/api/sessions")
async def list_sessions(username: str = Query("", description="按用户名过滤会话")):
    """获取会话列表，可通过 username 过滤"""
    return {"sessions": await memory_manager.list_sessions(username or None)}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """获取指定会话"""
    result = await memory_manager.get_session(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"session": result}


@app.post("/api/users")
async def register_user(request: UsernameRequest):
    """注册用户名"""
    try:
        username = memory_manager.register_username(request.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"username": username}


@app.get("/api/users")
async def list_users():
    """获取所有用户名"""
    return {"usernames": memory_manager.list_usernames()}


@app.get("/api/users/{username}/sessions")
async def list_user_sessions(username: str):
    """获取指定用户名下的 session_id 列表及会话摘要"""
    normalized = username.strip()[:12]
    if normalized not in memory_manager.list_usernames():
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    sessions = await memory_manager.list_user_sessions(normalized)
    return {
        "username": normalized,
        "session_ids": [item["session_id"] for item in sessions],
        "sessions": sessions,
    }


@app.get("/")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "2.0", "model": model.model, "agentscope": "2.0"}

