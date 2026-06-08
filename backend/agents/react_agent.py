import json
from typing import Any, AsyncGenerator, Dict, List

from agentscope.agent import Agent, ReActConfig
from agentscope.event import (
    EventType,
    TextBlockDeltaEvent,
    ThinkingBlockDeltaEvent,
    ToolCallStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolResultTextDeltaEvent,
    ToolResultEndEvent,
)
from agentscope.message import AssistantMsg, UserMsg
from agentscope.model import ChatModelBase
from agentscope.permission import PermissionMode
from agentscope.state import AgentState
from agentscope.tool import Toolkit

DEFAULT_SYSTEM_PROMPT = """你是一个智能助手，可以使用工具来帮助回答问题。

【效率要求】
- 每次只调用一个工具，拿到结果后立即组织回答，不要连续重复调用
- 问「明天/后天」日期：直接用 date_tool 的 add，days 设为 1 或 2，无需先调用 now
- 查询天气：使用 weather_tool；若用户问明天/后天，先用 date_tool 算出 YYYY-MM-DD 再传入 date 参数
- 查询新闻等非天气信息：使用 web_search，搜索词加上年份等具体关键词
- 已有工具返回结果时，禁止再次调用相同工具和相同参数

【12306 火车票 MCP】工具名以 mcp__12306_mcp__ 开头，常用：
- mcp__12306_mcp__get-current-date：获取当前日期
- mcp__12306_mcp__get-station-code-by-names / get-stations-code-in-city：查车站编码
- mcp__12306_mcp__get-tickets：查余票/车次（日期须 YYYY-MM-DD，不明确时先用 date_tool）
- mcp__12306_mcp__get-interline-tickets：联程票
- mcp__12306_mcp__get-train-route-stations：列车经停站
日期不明确时先用 date_tool，站名不明确时先查车站编码。

【全球酒店 MCP】工具名以 mcp__hotel_mcp__ 开头，常用：
- mcp__hotel_mcp__getHotelSearchTags：获取搜索标签/筛选项
- mcp__hotel_mcp__searchHotels：按区域/条件搜索酒店，每轮最多 1 次
  示例参数：{"place":"上海外滩","countryCode":"CN","checkInParam":{"checkInDate":"2026-06-10","stayNights":1,"adultCount":2},"filterOptions":{"starRatings":[5.0,5.0]}}
- mcp__hotel_mcp__getHotelDetail：查具体酒店价格/房型；有 hotelId 时优先传 hotelId，否则传 name
  示例参数：{"name":"重庆光成酒店","dateParam":{"checkInDate":"2026-06-11","checkOutDate":"2026-06-12"}}
getHotelDetail 可按需多次调用（换酒店名、hotelId 或日期），但相同参数不要重复调用。

【回答格式】
- 面向用户的最终回答必须使用 Markdown，结构清晰、易读
- 天气回答：开头一句简短结论，然后逐日分段；每一天必须用 ### 日期 作为标题
- 每个天气指标必须各占一行，以 - 列表展示
- 火车票/车次回答：禁止使用 Markdown 表格；按时段用 ### 分段，每个车次用引用块展示，格式：
  > **G19** · 北京南 → 上海虹桥
  > - 时间：14:00 → 18:32（4小时32分）
  > - 票价：二等座 有票 ¥661 · 一等座 有票 ¥1058
  结尾用 **💡 温馨提示：** 给出 1-2 条出行建议
- 酒店推荐/预订回答：禁止使用 Markdown 表格；每家酒店用引用块展示，结尾用 **💡 预订建议：**
"""


class ReActAgent:
    """基于 AgentScope 2.0 Agent 的 ReAct 智能体封装，兼容 OpenAI SSE 格式。"""

    def __init__(self, model: ChatModelBase, toolkit: Toolkit):
        self._model = model
        self._toolkit = toolkit
        self._base_system_prompt = DEFAULT_SYSTEM_PROMPT
        self._agent = Agent(
            name="assistant",
            system_prompt=self._base_system_prompt,
            model=model,
            toolkit=toolkit,
            react_config=ReActConfig(max_iters=10),
        )

    async def list_tools_async(self) -> List[Dict[str, Any]]:
        return await self._toolkit.get_tool_schemas()

    @staticmethod
    def _display_tool_name(name: str) -> str:
        if name.startswith("mcp__"):
            parts = name.split("__", 2)
            if len(parts) >= 3:
                return parts[2]
        return name

    def _prepare_agent(self, messages: List[Dict[str, Any]]) -> List[Any]:
        system_parts = [
            m["content"] for m in messages if m.get("role") == "system"
        ]
        if system_parts:
            self._agent._system_prompt = (  # noqa: SLF001
                self._base_system_prompt
                + "\n\n"
                + "\n\n".join(system_parts)
            )
        else:
            self._agent._system_prompt = self._base_system_prompt  # noqa: SLF001

        state = AgentState()
        state.permission_context.mode = PermissionMode.BYPASS
        self._agent.state = state

        agent_msgs = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                continue
            if role == "user":
                agent_msgs.append(UserMsg(name="user", content=content))
            elif role == "assistant":
                agent_msgs.append(AssistantMsg(name="assistant", content=content))
        return agent_msgs

    def _make_chunk(
        self,
        chunk_id: str | None,
        delta: dict,
        finish_reason: str | None = None,
    ) -> Dict[str, Any]:
        return {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": 0,
            "model": self._model.model,
            "choices": [{
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }],
        }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
    ) -> Any:
        agent_msgs = self._prepare_agent(messages)
        if stream:
            return self._chat_stream(agent_msgs)
        return await self._chat_non_stream(agent_msgs)

    async def _chat_non_stream(
        self,
        agent_msgs: List[Any],
    ) -> Dict[str, Any]:
        result = await self._agent.reply(agent_msgs)
        content = result.get_text_content() or ""
        usage = result.usage
        return {
            "id": result.id,
            "object": "chat.completion",
            "created": 0,
            "model": self._model.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {
                "input_tokens": usage.input_tokens if usage else 0,
                "output_tokens": usage.output_tokens if usage else 0,
            },
        }

    async def _chat_stream(
        self,
        agent_msgs: List[Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        chunk_id: str | None = None
        pending_tool_calls: dict[str, dict[str, Any]] = {}
        pending_tool_results: dict[str, str] = {}

        async for event in self._agent.reply_stream(agent_msgs):
            if chunk_id is None and hasattr(event, "reply_id"):
                chunk_id = event.reply_id

            if isinstance(event, TextBlockDeltaEvent):
                if event.delta:
                    yield self._make_chunk(chunk_id, {"content": event.delta})

            elif isinstance(event, ThinkingBlockDeltaEvent):
                if event.delta:
                    yield self._make_chunk(
                        chunk_id,
                        {"content": "", "thinking": event.delta},
                    )

            elif isinstance(event, ToolCallStartEvent):
                yield self._make_chunk(chunk_id, {"content_reset": True})
                display_name = self._display_tool_name(event.tool_call_name)
                yield self._make_chunk(
                    chunk_id,
                    {
                        "content": "",
                        "thinking": f"正在调用 {display_name} 获取信息…",
                    },
                )
                pending_tool_calls[event.tool_call_id] = {
                    "name": display_name,
                    "arguments": {},
                    "input_json": "",
                }

            elif isinstance(event, ToolCallDeltaEvent):
                entry = pending_tool_calls.get(event.tool_call_id)
                if entry is not None:
                    entry["input_json"] += event.delta

            elif isinstance(event, ToolCallEndEvent):
                entry = pending_tool_calls.get(event.tool_call_id)
                if entry is not None:
                    try:
                        entry["arguments"] = json.loads(entry["input_json"] or "{}")
                    except json.JSONDecodeError:
                        entry["arguments"] = {}

            elif isinstance(event, ToolResultTextDeltaEvent):
                pending_tool_results[event.tool_call_id] = (
                    pending_tool_results.get(event.tool_call_id, "") + event.delta
                )

            elif isinstance(event, ToolResultEndEvent):
                entry = pending_tool_calls.get(event.tool_call_id)
                if entry is not None:
                    result_text = pending_tool_results.get(event.tool_call_id, "")
                    yield self._make_chunk(
                        chunk_id,
                        {
                            "content": "",
                            "tool_call": {
                                "name": entry["name"],
                                "arguments": entry["arguments"],
                                "result": result_text,
                            },
                        },
                    )
                    pending_tool_calls.pop(event.tool_call_id, None)
                    pending_tool_results.pop(event.tool_call_id, None)

            elif event.type == EventType.REPLY_END:
                yield self._make_chunk(chunk_id, {}, finish_reason="stop")
