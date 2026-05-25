# AgentScope Chat API

基于 FastAPI + AgentScope (OpenAIChatModel) 构建的大模型对话接口，支持 SSE 流式响应、会话记忆和 OpenAI 兼容格式。

## 功能特性

- **SSE 流式输出** — 实时逐 token 返回，延迟低
- **会话记忆** — 基于 `session_id` 的多轮对话上下文管理
- **OpenAI 兼容格式** — 流式/非流式响应均遵循 OpenAI Chat Completions 格式
- **System Prompt** — 支持在请求中传入 system 消息
- **Token 用量统计** — 每轮返回 `usage` 信息

## 环境要求

- Python >= 3.12
- uv（推荐）或 pip

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

创建或编辑 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

> 支持任意 OpenAI 兼容 API（OpenAI、Azure、硅基流动等），只需修改 `base_url` 和 `model_name`。

### 3. 启动服务

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：http://localhost:8000/docs（Swagger UI）

## 接口说明

### POST /api/chat

**请求体：**

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `messages` | `list[ChatMessage]` | 必填 | 消息列表 |
| `stream` | `bool` | `true` | 是否使用 SSE 流式响应 |
| `session_id` | `str` | `""` | 会话 ID，空则自动生成并返回 |

**ChatMessage 结构：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `role` | `str` | 角色：`user` / `assistant` / `system` |
| `content` | `str` | 消息内容 |

### 示例

#### 流式响应（默认）

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

**响应头** — 新会话时返回 `X-Session-Id`，用于后续请求：

```
X-Session-Id: a1b2c3d4e5f6
```

**SSE 响应格式：**

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-v4-flash","choices":[{"index":0,"delta":{"content":"你"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-v4-flash","choices":[{"index":0,"delta":{"content":"好"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-v4-flash","choices":[{"index":0,"delta":{"content":""},"finish_reason":null,"usage":{"input_tokens":5,"output_tokens":2}}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-v4-flash","choices":[{"index":0,"delta":{"content":""},"finish_reason":"stop"}]}

data: [DONE]
```

#### 非流式响应

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}],
    "stream": false
  }'
```

**响应体：**

```json
{
  "session_id": "a1b2c3d4e5f6",
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-v4-flash",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "你好，有什么可以帮助你的吗？"},
      "finish_reason": "stop"
    }
  ],
  "usage": {"input_tokens": 5, "output_tokens": 12}
}
```

#### 多轮对话（携带 session_id）

```bash
# 首次对话
SESSION=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "我叫张三"}], "stream": false}' \
  | python -c "import sys,json; print(json.load(sys.stdin)[\"session_id\"])")

# 后续对话
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [{\"role\": \"user\", \"content\": \"我叫什么名字？\"}],
    \"session_id\": \"$SESSION\",
    \"stream\": false
  }"
# 模型会正确回答"张三"
```

#### 携带 System Prompt

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "你是一个友好的中文助手。"},
      {"role": "user", "content": "你好"}
    ],
    "session_id": "a1b2c3d4e5f6"
  }'
```

## 项目结构

```
.
├── main.py          # FastAPI 应用入口
├── pyproject.toml   # 项目依赖配置
├── .env             # 环境变量（API Key 等，不提交）
└── README.md
```

## 技术栈

- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架
- [AgentScope](https://github.com/modelscope/agentscope) — 模型封装（OpenAIChatModel）
- [Uvicorn](https://www.uvicorn.org/) — ASGI 服务器
- [InMemoryMemory](https://modelscope.github.io/agentscope/) — 会话记忆存储

## 扩展建议

- **持久化记忆**：将 `InMemoryMemory` 替换为 `RedisMemory` 或 `AsyncSQLAlchemyMemory`
- **分布式部署**：改用共享存储（Redis/数据库）替代进程内 dict 存储 sessions
- **鉴权**：在 `/api/chat` 端点前添加 API Key 校验中间件
- **对话历史上限**：在 `build_messages_with_history` 中限制返回的历史消息条数，控制 token 消耗
