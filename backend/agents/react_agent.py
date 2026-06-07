import json
import re
from typing import List, Dict, Any, AsyncGenerator, Optional

from agentscope.model import OpenAIChatModel

from tools import tool_registry, BaseTool
from memory.file_backend import FileBackend


class ReActAgent:
    """ReAct智能体，实现思考-行动循环"""

    MAX_TOOL_ROUNDS = 10
    _SINGLE_CALL_TOOLS = frozenset({
        "searchHotels",
        "getHotelSearchTags",
    })

    _WEATHER_KEYWORDS = re.compile(
        r"天气|气温|温度|下雨|下雪|降雨|降水|预报|几度|冷不冷|热不热|带伞"
    )
    _RELATIVE_DAY_MAP = {"今天": 0, "明天": 1, "后天": 2, "大后天": 3}
    _INVALID_CITIES = frozenset({
        "天", "未来", "今天", "明天", "后天", "大后天",
        "天气", "气温", "温度", "下", "的",
    })
    _FILLER_PREFIX = re.compile(
        r"^(?:请|帮我|帮忙|查询下|查一下|查下|查询|看看|想知道|告诉我|请问|说下|说一下|麻烦)"
        r"[\s，,：:]*"
    )
    _CITY_TOKEN = r"[\u4e00-\u9fff]{2,8}(?:市|县|区)?"

    def __init__(self, model: OpenAIChatModel):
        self._model = model
        self._tools = {name: cls() for name, cls in tool_registry.items()}
        self._tool_cache: dict[str, str] = {}
        self._single_call_tools_used: set[str] = set()
        self._pending_orchestration_events: list[dict[str, Any]] = []

    def register_tools(self, extra_tools: dict[str, BaseTool]) -> None:
        """注册额外工具（如 MCP）。"""
        self._tools.update(extra_tools)

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具的描述"""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def _extract_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """从模型响应中提取工具调用"""
        if not content or not content.strip():
            return None
            
        try:
            # 1. 尝试匹配```json ... ``` 格式
            match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            
            # 2. 尝试匹配 ``` ... ``` 格式（不带json标记
            match = re.search(r'```\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            
            # 3. 尝试提取 { ... } 格式
            match = re.search(r'(\{.*"name".*"arguments".*\})', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            
            # 4. 直接尝试解析（处理只包含JSON的情况
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "name" in parsed:
                    return parsed
            except:
                pass
                
            return None
        except:
            return None
    
    def _looks_like_tool_call(self, content: str) -> bool:
        """判断文本是否可能是工具调用（用于抑制流式输出）"""
        if not content or not content.strip():
            return False
        stripped = content.strip()
        # 以 { 开头即视为工具调用，避免 {"name 等片段被流式输出
        if stripped.startswith("{"):
            return True
        if stripped.startswith("```"):
            return True
        return self._extract_tool_call(content) is not None

    def _strip_tool_call_text(self, content: str) -> str:
        """从文本中移除工具调用 JSON，保留可展示的自然语言"""
        if not content:
            return ""
        cleaned = re.sub(
            r'```json\s*\{.*?\}\s*```', '', content, flags=re.DOTALL
        )
        cleaned = re.sub(
            r'```\s*\{.*?"name".*?"arguments".*?\}\s*```', '', cleaned, flags=re.DOTALL
        )
        cleaned = re.sub(
            r'\{"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{.*?\}\s*\}',
            '', cleaned, flags=re.DOTALL
        )
        return cleaned.strip()
    
    def _tool_cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        return f"{tool_name}:{json.dumps(arguments, ensure_ascii=False, sort_keys=True)}"

    def _get_last_user_message(self, messages: List[Dict[str, Any]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                return content if isinstance(content, str) else ""
        return ""

    def _normalize_city_name(self, raw: str) -> Optional[str]:
        if not raw:
            return None
        city = re.sub(r"的$", "", raw.strip())
        city = re.sub(r"(市|县|区)$", "", city).strip()
        if len(city) < 2 or city in self._INVALID_CITIES:
            return None
        if re.search(r"未来|天气|气温|温度", city):
            return None
        return city

    def _parse_weather_query(self, text: str) -> Optional[Dict[str, Any]]:
        """解析天气问题中的城市、相对日期、未来 N 天预报。"""
        if not text or not self._WEATHER_KEYWORDS.search(text):
            return None

        cleaned = self._FILLER_PREFIX.sub("", text.strip())
        city: Optional[str] = None
        days_offset: Optional[int] = None
        forecast_days: Optional[int] = None

        multi_day = re.match(
            rf"^({self._CITY_TOKEN})\s*未来\s*(\d+)\s*天",
            cleaned,
        )
        if multi_day:
            city = self._normalize_city_name(multi_day.group(1))
            forecast_days = int(multi_day.group(2))

        if not city:
            city_first = re.match(
                rf"^({self._CITY_TOKEN})\s*(今天|明天|后天|大后天)",
                cleaned,
            )
            if city_first:
                city = self._normalize_city_name(city_first.group(1))
                days_offset = self._RELATIVE_DAY_MAP.get(city_first.group(2))

        if not city:
            day_first = re.match(
                rf"^(今天|明天|后天|大后天)\s*({self._CITY_TOKEN})",
                cleaned,
            )
            if day_first:
                days_offset = self._RELATIVE_DAY_MAP.get(day_first.group(1))
                city = self._normalize_city_name(day_first.group(2))

        if not city:
            simple = re.match(
                rf"^({self._CITY_TOKEN})\s*(?:的\s*)?"
                r"(?:天气|气温|温度|下雨|下雪|降雨|降水|预报)",
                cleaned,
            )
            if simple:
                city = self._normalize_city_name(simple.group(1))

        if not city:
            return None

        result: Dict[str, Any] = {"city": city, "days_offset": days_offset}
        if forecast_days is not None:
            result["forecast_days"] = forecast_days
        return result

    def _extract_date_from_tool_result(self, result: str) -> Optional[str]:
        match = re.search(r"结果日期[：:]\s*(\d{4}-\d{2}-\d{2})", result)
        return match.group(1) if match else None

    async def _run_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        auto: bool = False,
    ) -> str:
        if tool_name not in self._tools:
            return f"错误：未知工具 '{tool_name}'"

        cache_key = self._tool_cache_key(tool_name, arguments)
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]

        tool: BaseTool = self._tools[tool_name]
        try:
            result = await tool.execute(**arguments)
            self._tool_cache[cache_key] = result
            if auto:
                self._pending_orchestration_events.append({
                    "thinking": f"正在自动调用 {tool_name} 获取信息…",
                    "tool_call": {
                        "name": tool_name,
                        "arguments": arguments,
                        "result": result,
                    },
                })
            return result
        except Exception as e:
            return f"工具执行错误：{str(e)}"

    async def _prepare_weather_orchestration(self, messages: List[Dict[str, Any]]) -> bool:
        """天气类问题：自动 date_tool（如需）→ weather_tool，再让模型直接作答。"""
        parsed = self._parse_weather_query(self._get_last_user_message(messages))
        if not parsed:
            return False

        city = parsed["city"]
        days_offset = parsed.get("days_offset")
        date_str: Optional[str] = None

        if days_offset is not None and days_offset > 0:
            date_args = {"action": "add", "days": days_offset}
            date_result = await self._run_tool("date_tool", date_args, auto=True)
            messages.append({
                "role": "system",
                "content": f"工具执行结果（自动编排-date_tool）：\n{date_result}",
            })
            date_str = self._extract_date_from_tool_result(date_result)

        weather_args: Dict[str, Any] = {"city": city}
        if date_str:
            weather_args["date"] = date_str
        weather_result = await self._run_tool("weather_tool", weather_args, auto=True)
        messages.append({
            "role": "system",
            "content": f"工具执行结果（自动编排-weather_tool）：\n{weather_result}",
        })

        hint = (
            f"【系统提示】天气查询所需工具已自动完成，请根据上述工具结果"
            f"直接用 Markdown 组织最终回答，不要再调用 date_tool 或 weather_tool。"
            f" 用户查询的城市是「{city}」，回答中必须使用工具返回的该城市数据，"
            f"禁止引用其他城市或历史对话中的天气信息。"
        )
        forecast_days = parsed.get("forecast_days")
        if forecast_days:
            hint += (
                f" 用户询问未来 {forecast_days} 天预报，请按天逐条列出天气、温度、风力等信息。"
            )
        messages.append({"role": "system", "content": hint})
        return True

    def _make_tool_chunks(
        self,
        chunk_id: Optional[str],
        thinking: str,
        tool_call: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": 0,
                "model": self._model.model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"content_reset": True},
                    "finish_reason": None,
                }],
            },
            {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": 0,
                "model": self._model.model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"content": "", "thinking": thinking},
                    "finish_reason": None,
                }],
            },
            {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": 0,
                "model": self._model.model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"content": "", "tool_call": tool_call},
                    "finish_reason": None,
                }],
            },
        ]

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具调用，相同参数在本轮对话中只执行一次"""
        if tool_name not in self._tools:
            return f"错误：未知工具 '{tool_name}'"

        if (
            tool_name in self._SINGLE_CALL_TOOLS
            and tool_name in self._single_call_tools_used
        ):
            return (
                f"本轮对话已调用过 {tool_name}，请根据之前的工具结果直接回答用户，"
                f"不要再次调用该工具。"
            )

        cache_key = self._tool_cache_key(tool_name, arguments)
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]

        tool: BaseTool = self._tools[tool_name]
        try:
            result = await tool.execute(**arguments)
            self._tool_cache[cache_key] = result
            if tool_name in self._SINGLE_CALL_TOOLS:
                self._single_call_tools_used.add(tool_name)
            return result
        except Exception as e:
            return f"工具执行错误：{str(e)}"
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        memory: Optional[FileBackend] = None,
        stream: bool = False,
    ) -> Any:
        """执行聊天逻辑，支持工具调用"""
        self._tool_cache = {}
        self._single_call_tools_used = set()
        self._pending_orchestration_events = []
        # 如果有工具，添加工具描述到系统消息
        if self._tools:
            tools_desc = json.dumps(self.tools, ensure_ascii=False)
            tool_prompt = f"""你是一个智能助手，可以使用以下工具来帮助回答问题：
{tools_desc}

【重要规则】
1. 如果需要调用工具，请**只输出**纯JSON格式，不要包含任何其他文字或说明
2. 不要输出"思考"、"我需要调用"等描述性文字
3. 如果不需要调用工具，请直接回答用户问题

【工具调用示例】
正确：
{{"name": "calculator", "arguments": {{"query": "2+3"}}}}

错误（不要这样）：
我需要计算2+3，我将使用calculator工具
{{"name": "calculator", "arguments": {{"query": "2+3"}}}}

【决策逻辑】
- 需要实时数据/特定功能 → 输出纯JSON调用工具
- 已有足够信息 → 直接回答

【效率要求】
- 每次只调用一个工具，拿到结果后立即组织回答，不要连续重复调用
- 问「明天/后天」日期：直接用 date_tool 的 add，days 设为 1 或 2，无需先调用 now，也无需传 date_str
- 查询天气：使用 weather_tool；若用户问明天/后天，先用 date_tool 算出 YYYY-MM-DD 再传入 date 参数；不要用 web_search 查天气
- 查询新闻等非天气信息：使用 web_search，搜索词加上年份等具体关键词，避免「明天」「后天」等相对时间词
- 查询火车票、车次、余票、车站信息：使用 12306 MCP 工具；日期不明确时先用 date_tool 获取或推算 YYYY-MM-DD；站名不明确时可先调用车站查询类工具
- 按区域/条件找酒店：用 searchHotels，每轮最多 1 次；示例：{{"name":"searchHotels","arguments":{{"place":"上海外滩","countryCode":"CN","checkInParam":{{"checkInDate":"2026-06-10","stayNights":1,"adultCount":2}},"filterOptions":{{"starRatings":[5.0,5.0]}}}}}}
- 查询**具体某家酒店**的价格/房型：用 getHotelDetail；若只有酒店名用 name 参数，若已从 searchHotels 拿到 hotelId 则优先传 hotelId；示例：{{"name":"getHotelDetail","arguments":{{"name":"重庆光成酒店","dateParam":{{"checkInDate":"2026-06-11","checkOutDate":"2026-06-12"}}}}}}
- getHotelDetail 可按需多次调用（如换酒店名、换 hotelId、换日期），但相同参数不要重复调用；若暂无房型可换日期或先用 searchHotels 找 hotelId 再查详情
- 已有工具返回结果时，禁止再次调用相同工具和相同参数

【回答格式】
- 面向用户的最终回答必须使用 Markdown，结构清晰、易读
- 天气回答：开头一句简短结论，然后逐日分段；每一天必须用 ### 日期（今天/明天） 作为标题并单独占一行
- 每个天气指标（天气、温度、风力、湿度等）必须各占一行，以 - 列表展示，禁止挤在同一段
- 多日预报示例格式：
  ### 2026-06-01（明天）
  - 天气：白天多云，夜间晴
  - 温度：22°C ~ 33°C
  - 风力：南风 1-3 级
- 结尾可加 **总体趋势：** 一段简短总结
- 火车票/车次回答：**禁止使用 Markdown 表格**；按时段用 ### 分段（如 ### 🌙 晚间出发），每个车次用引用块展示，格式如下：
  > **G19** · 北京南 → 上海虹桥
  > - 时间：14:00 → 18:32（4小时32分）
  > - 票价：二等座 有票 ¥661 · 一等座 有票 ¥1058
  结尾用 **💡 温馨提示：** 给出 1-2 条出行建议
- 酒店推荐/预订回答：**禁止使用 Markdown 表格**；每家酒店用引用块展示，格式如下：
  > **上海外滩华尔道夫酒店** · ⭐⭐⭐⭐⭐
  > - 地址：上海市黄浦区中山东一路2号
  > - 入住：2026-06-10 → 离店：2026-06-12（2晚）
  > - 价格：¥2,880/晚起 · 含早 · 可免费取消
  可按价格/评分/位置分组，结尾用 **💡 预订建议：** 给出 1-2 条建议"""
            
            # 查找或创建系统消息
            system_msg_exists = any(m["role"] == "system" for m in messages)
            if system_msg_exists:
                for m in messages:
                    if m["role"] == "system":
                        m["content"] = tool_prompt + "\n\n" + m["content"]
                        break
            else:
                messages.insert(0, {"role": "system", "content": tool_prompt})

        weather_ready = await self._prepare_weather_orchestration(messages)
        allow_tools = not weather_ready

        if stream:
            return self._chat_stream(messages, memory, tool_round=0, allow_tools=allow_tools)
        else:
            return await self._chat_non_stream(messages, memory, tool_round=0, allow_tools=allow_tools)
    
    async def _chat_non_stream(
        self,
        messages: List[Dict[str, Any]],
        memory: Optional[FileBackend],
        tool_round: int = 0,
        allow_tools: bool = True,
    ) -> Dict[str, Any]:
        """非流式聊天"""
        full_text = ""
        final_usage = None
        first_chunk_id = None
        
        stream = await self._model(messages)
        async for chunk in stream:
            if first_chunk_id is None:
                first_chunk_id = getattr(chunk, "id", None)
            for block in chunk.content:
                if block["type"] == "text":
                    full_text = block["text"]
            if chunk.usage:
                final_usage = chunk.usage
        
        tool_call = self._extract_tool_call(full_text) if allow_tools else None
        if tool_call and "name" in tool_call:
            if tool_round < self.MAX_TOOL_ROUNDS:
                tool_result = await self._execute_tool(
                    tool_call["name"],
                    tool_call.get("arguments", {})
                )
                messages.append({
                    "role": "system",
                    "content": f"工具执行结果：\n{tool_result}"
                })
                return await self._chat_non_stream(
                    messages, memory, tool_round + 1, allow_tools=True
                )
            messages.append({
                "role": "system",
                "content": "工具调用次数已达上限。请根据已有工具结果，直接用自然语言回答用户，不要输出 JSON。",
            })
            return await self._chat_non_stream(
                messages, memory, tool_round + 1, allow_tools=False
            )

        answer = self._strip_tool_call_text(full_text) or full_text
        return {
            "id": first_chunk_id,
            "object": "chat.completion",
            "created": 0,
            "model": self._model.model_name,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop"
            }],
            "usage": {
                "input_tokens": final_usage.input_tokens if final_usage else 0,
                "output_tokens": final_usage.output_tokens if final_usage else 0
            }
        }
    
    async def _chat_stream(
        self,
        messages: List[Dict[str, Any]],
        memory: Optional[FileBackend],
        tool_round: int = 0,
        allow_tools: bool = True,
    ) -> AsyncGenerator[str, None]:
        """流式聊天"""
        chunk_id = None
        if self._pending_orchestration_events:
            for event in self._pending_orchestration_events:
                for out_chunk in self._make_tool_chunks(
                    chunk_id,
                    event["thinking"],
                    event["tool_call"],
                ):
                    yield out_chunk
            self._pending_orchestration_events = []

        full_text = ""
        sent_length = 0
        suppress_stream = False

        stream = await self._model(messages)
        async for chunk in stream:
            if chunk_id is None:
                chunk_id = getattr(chunk, "id", None)

            for block in chunk.content:
                if block["type"] == "text":
                    full_text = block["text"]
                    if self._looks_like_tool_call(full_text):
                        suppress_stream = True
                    if not suppress_stream:
                        delta = full_text[sent_length:]
                        sent_length = len(full_text)
                        if delta:
                            yield {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": 0,
                                "model": self._model.model_name,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": delta},
                                    "finish_reason": None
                                }]
                            }
        
        tool_call = self._extract_tool_call(full_text) if allow_tools else None
        if tool_call and "name" in tool_call:
            if tool_round < self.MAX_TOOL_ROUNDS:
                yield {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": self._model.model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {"content_reset": True},
                        "finish_reason": None
                    }]
                }
                
                yield {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": self._model.model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": "",
                            "thinking": f"正在调用 {tool_call['name']} 获取信息…"
                        },
                        "finish_reason": None
                    }]
                }
                
                tool_result = await self._execute_tool(
                    tool_call["name"],
                    tool_call.get("arguments", {})
                )
                
                yield {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": self._model.model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": "",
                            "tool_call": {
                                "name": tool_call["name"],
                                "arguments": tool_call.get("arguments", {}),
                                "result": tool_result
                            }
                        },
                        "finish_reason": None
                    }]
                }
                
                messages.append({
                    "role": "system",
                    "content": f"工具执行结果：\n{tool_result}"
                })
                
                async for response in self._chat_stream(
                    messages, memory, tool_round + 1, allow_tools=True
                ):
                    yield response
                return

            messages.append({
                "role": "system",
                "content": "工具调用次数已达上限。请根据已有工具结果，直接用自然语言回答用户，不要输出 JSON。",
            })
            async for response in self._chat_stream(
                messages, memory, tool_round + 1, allow_tools=False
            ):
                yield response
            return
        
        if suppress_stream and sent_length < len(full_text):
            remaining = self._strip_tool_call_text(full_text[sent_length:])
            if remaining:
                yield {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": self._model.model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": remaining},
                        "finish_reason": None
                    }]
                }
        
        yield {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": 0,
            "model": self._model.model_name,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
