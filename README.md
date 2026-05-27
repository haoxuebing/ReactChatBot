# AgentScope Chat API

基于 FastAPI + AgentScope 构建的大模型对话接口，支持 **ReAct 智能体**（思考-行动循环）、**工具调用**、**SSE 流式响应**和**会话记忆管理**。

## 功能特性

- **ReAct 智能体** — 自主思考-行动循环，根据问题自动决定是否调用工具
- **工具调用** — 内置计算器、日期工具、网络搜索等工具，模型可自主调用
- **SSE 流式输出** — 实时逐 token 返回，延迟低
- **会话记忆** — 基于 `session_id` 的多轮对话上下文管理
- **OpenAI 兼容格式** — 流式/非流式响应均遵循 OpenAI Chat Completions 格式
- **System Prompt** — 支持在请求中传入 system 消息
- **Token 用量统计** — 每轮返回 `usage` 信息
- **会话管理 API** — 查看、获取、删除会话

## 环境要求

- Python >= 3.12
- uv（推荐）或 pip
- ChromeDriver（使用 WebSearchTool 时需要）

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
CHROMEDRIVER_PATH=C:\path\to\chromedriver.exe
```

> 支持任意 OpenAI 兼容 API（OpenAI、Azure、硅基流动等），只需修改 `base_url` 和 `model_name`。
> `CHROMEDRIVER_PATH` 仅在启用 WebSearchTool 时需要。

### 3. 启动服务

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：http://localhost:8000/docs（Swagger UI）

## 项目结构

```
.
├── main.py                  # FastAPI 应用入口，路由定义
├── pyproject.toml           # 项目依赖配置
├── .env                     # 环境变量（API Key 等，不提交）
├── .gitignore
├── .python-version
│
├── agents/
│   ├── __init__.py
│   └── react_agent.py       # ReAct 智能体，实现思考-行动循环
│
├── schemas/
│   ├── __init__.py
│   ├── chat_request.py      # 聊天请求模型（含 AgentConfig）
│   ├── chat_message.py      # 聊天消息模型
│   └── agent_config.py      # 智能体配置（temperature、memory_limit 等）
│
├── memory/
│   ├── __init__.py
│   ├── memory_manager.py    # 会话级记忆管理器
│   └── in_memory_backend.py # 基于 AgentScope InMemoryMemory 的记忆后端
│
└── tools/
    ├── __init__.py           # 工具注册表
    ├── base_tool.py          # 工具基类
    ├── calculator_tool.py    # 计算器工具（数学运算）
    ├── date_tool.py          # 日期工具（当前时间、格式化、加减、差值）
    └── web_search_tool.py    # 网络搜索工具（基于 Selenium + ChromeDriver）
```

## 接口说明

### POST /api/chat

智能体聊天接口。模型会自动判断是否需要调用工具来回答问题。

**请求体：**

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `messages` | `list[ChatMessage]` | 必填 | 消息列表 |
| `stream` | `bool` | `true` | 是否使用 SSE 流式响应 |
| `session_id` | `str` | `""` | 会话 ID，空则自动生成并返回 |
| `agent_config` | `AgentConfig` | `{}` | 智能体配置 |

**AgentConfig 字段：**

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enable_tools` | `bool` | `true` | 是否启用工具调用 |
| `memory_limit` | `int` | `100` | 记忆消息上限 |
| `temperature` | `float` | `0.7` | 模型温度参数 |

**ChatMessage 结构：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `role` | `str` | 角色：`user` / `assistant` / `system` |
| `content` | `str` | 消息内容 |

### GET /api/tools

获取所有可用工具列表。

### GET /api/sessions

获取所有活跃会话列表（含消息数量）。

### GET /api/sessions/{session_id}

获取指定会话的详细信息（含对话历史内容）。

### DELETE /api/sessions/{session_id}

删除指定会话。

### GET /

健康检查接口。

## 使用示例

### 流式聊天（默认）

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

新会话时响应头包含 `X-Session-Id`，用于后续请求。

### 工具调用示例

模型会自动识别需要调用工具的问题：

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "计算 2 + 3 * 4 等于多少？"}],
    "stream": false
  }'
```

模型会自主调用 `calculator` 工具并返回结果。

### 日期工具

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "今天是几号？"}],
    "stream": false
  }'
```

### 多轮对话

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
```

### 携带 System Prompt

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "你是一个友好的中文助手，喜欢用简洁的方式回答问题。"},
      {"role": "user", "content": "介绍一下你自己"}
    ]
  }'
```

## 技术栈

- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架
- [AgentScope](https://github.com/modelscope/agentscope) — 模型封装（OpenAIChatModel）与记忆存储（InMemoryMemory）
- [Uvicorn](https://www.uvicorn.org/) — ASGI 服务器
- [Selenium](https://www.selenium.dev/) — 浏览器自动化（WebSearchTool）

## 内置工具

| 工具 | 名称 | 说明 |
|---|---|---|
| 计算器 | `calculator` | 数学运算，支持加减乘除、幂运算、开方、三角函数等 |
| 日期工具 | `date_tool` | 获取当前时间、日期格式化、日期加减、日期差计算 |
| 网络搜索 | `web_search` | 基于 Selenium + ChromeDriver 的互联网搜索 |

## 扩展建议

- **持久化记忆**：将 `InMemoryMemory` 替换为 `RedisMemory` 或 `AsyncSQLAlchemyMemory`
- **分布式部署**：改用共享存储（Redis/数据库）替代进程内 dict 存储 sessions
- **自定义工具**：继承 `BaseTool` 实现 `execute` 方法，并在 `tools/__init__.py` 中注册
- **鉴权**：在 `/api/chat` 端点前添加 API Key 校验中间件
- **对话历史上限**：在 `build_messages_with_history` 中限制返回的历史消息条数，控制 token 消耗
