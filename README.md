# AgentScope Chat API

基于 FastAPI + AgentScope + Vue 构建的大模型对话应用，支持 **ReAct 智能体**（思考-行动循环）、**工具调用**、**SSE 流式响应**和**会话记忆管理**。

## 功能特性

- **ReAct 智能体** — 自主思考-行动循环，根据问题自动决定是否调用工具
- **工具调用** — 内置计算器、日期工具、网络搜索等工具，模型可自主调用
- **SSE 流式输出** — 实时逐 token 返回，延迟低
- **会话记忆** — 基于 `session_id` 的多轮对话上下文管理
- **OpenAI 兼容格式** — 流式/非流式响应均遵循 OpenAI Chat Completions 格式
- **System Prompt** — 支持在请求中传入 system 消息
- **Token 用量统计** — 每轮返回 `usage` 信息
- **会话管理 API** — 查看、获取、删除会话
- **Web UI** — 基于 Vue 3 的聊天界面，支持实时流式消息展示

## 环境要求

- Python >= 3.12
- Node.js >= 18
- uv（推荐）或 pip
- 可访问 `cn.bing.com`（使用 WebSearchTool 时需要）

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
uv sync
```

### 2. 配置环境变量

在 `backend` 目录下创建或编辑 `.env` 文件：

```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

> 支持任意 OpenAI 兼容 API（OpenAI、Azure、硅基流动等），只需修改 `base_url` 和 `model_name`。

### 3. 启动后端服务

```bash
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# 或者
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：http://localhost:8000/docs（Swagger UI）

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

### 5. 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端启动后访问：http://localhost:5173

## 项目结构

```
.
├── backend/                    # 后端代码（FastAPI + AgentScope）
│   ├── main.py                # FastAPI 应用入口，路由定义
│   ├── pyproject.toml         # 项目依赖配置
│   ├── .env                   # 环境变量（API Key 等，不提交）
│   ├── .python-version
│   └── uv.lock
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   └── react_agent.py     # ReAct 智能体，实现思考-行动循环
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat_request.py    # 聊天请求模型（含 AgentConfig）
│   │   ├── chat_message.py    # 聊天消息模型
│   │   └── agent_config.py    # 智能体配置（temperature、memory_limit 等）
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── memory_manager.py  # 会话级记忆管理器
│   │   └── in_memory_backend.py # 基于 AgentScope InMemoryMemory 的记忆后端
│   │
│   └── tools/
│       ├── __init__.py        # 工具注册表
│       ├── base_tool.py       # 工具基类
│       ├── calculator_tool.py # 计算器工具（数学运算）
│       ├── date_tool.py       # 日期工具（当前时间、格式化、加减、差值）
│       ├── web_search_tool.py # 网络搜索工具（必应中文搜索）
│       └── bing_client.py     # 必应搜索与网页抓取客户端
│
├── frontend/                   # 前端代码（Vue 3 + Vite）
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout.vue     # 主布局组件
│   │   │   ├── Sidebar.vue    # 侧边栏（会话列表）
│   │   │   ├── ChatArea.vue   # 聊天区域
│   │   │   ├── MessageBubble.vue # 消息气泡
│   │   │   └── MarkdownRenderer.vue # Markdown 渲染组件
│   │   ├── services/
│   │   │   └── api.js         # API 服务封装
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── .gitignore
└── README.md
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

### 后端
- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架
- [AgentScope](https://github.com/modelscope/agentscope) — 模型封装（OpenAIChatModel）与记忆存储（InMemoryMemory）
- [Uvicorn](https://www.uvicorn.org/) — ASGI 服务器
- [httpx](https://www.python-httpx.org/) — HTTP 客户端（必应搜索）
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) — HTML 解析（搜索结果与网页抓取）

### 前端
- [Vue 3](https://vuejs.org/) — 前端框架
- [Vite](https://vitejs.dev/) — 构建工具
- [TailwindCSS 3](https://tailwindcss.com/) — CSS 框架
- [Lucide Icons](https://lucide.dev/) — 图标库
- [markdown-it](https://markdown-it.github.io/) — Markdown 渲染
- [highlight.js](https://highlightjs.org/) — 代码高亮

## 内置工具

| 工具 | 名称 | 说明 |
|---|---|---|
| 计算器 | `calculator` | 数学运算，支持加减乘除、幂运算、开方、三角函数等 |
| 日期工具 | `date_tool` | 获取当前时间、日期格式化、日期加减、日期差计算 |
| 网络搜索 | `web_search` | 必应中文搜索，自动抓取 Top 结果正文，无需 API Key |

## 扩展建议

- **持久化记忆**：将 `InMemoryMemory` 替换为 `RedisMemory` 或 `AsyncSQLAlchemyMemory`
- **分布式部署**：改用共享存储（Redis/数据库）替代进程内 dict 存储 sessions
- **自定义工具**：继承 `BaseTool` 实现 `execute` 方法，并在 `tools/__init__.py` 中注册
- **鉴权**：在 `/api/chat` 端点前添加 API Key 校验中间件
- **对话历史上限**：在 `build_messages_with_history` 中限制返回的历史消息条数，控制 token 消耗
- **深色主题**：在前端中添加深色/浅色主题切换功能
