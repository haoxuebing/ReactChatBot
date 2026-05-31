import json
import re
from typing import List, Dict, Any, AsyncGenerator, Optional

from agentscope.model import OpenAIChatModel

from tools import tool_registry, BaseTool
from memory.file_backend import FileBackend


class ReActAgent:
    """ReAct智能体，实现思考-行动循环"""
    
    MAX_TOOL_ROUNDS = 3
    
    def __init__(self, model: OpenAIChatModel):
        self._model = model
        self._tools = {name: cls() for name, cls in tool_registry.items()}
        self._tool_cache: dict[str, str] = {}
    
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
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具调用，相同参数在本轮对话中只执行一次"""
        if tool_name not in self._tools:
            return f"错误：未知工具 '{tool_name}'"

        cache_key = self._tool_cache_key(tool_name, arguments)
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]
        
        tool: BaseTool = self._tools[tool_name]
        try:
            result = await tool.execute(**arguments)
            self._tool_cache[cache_key] = result
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
- 查询天气/新闻：先用 date_tool 算出具体日期，再用 web_search 搜索「城市 YYYY-MM-DD 天气预报」等具体关键词
- 搜索时禁止使用「明天」「后天」等相对时间词，必须替换为具体日期
- 已有工具返回结果时，禁止再次调用相同工具和相同参数

【回答格式】
- 面向用户的最终回答必须使用 Markdown，结构清晰、易读
- 多项信息（如多日天气）用 ### 小标题分段，每项指标单独一行
- 使用 - 列表展示温度、湿度、风力等字段，不要挤在同一段
- 开头先给一句简短结论，再展开细节"""
            
            # 查找或创建系统消息
            system_msg_exists = any(m["role"] == "system" for m in messages)
            if system_msg_exists:
                for m in messages:
                    if m["role"] == "system":
                        m["content"] = tool_prompt + "\n\n" + m["content"]
                        break
            else:
                messages.insert(0, {"role": "system", "content": tool_prompt})
        
        if stream:
            return self._chat_stream(messages, memory, tool_round=0, allow_tools=True)
        else:
            return await self._chat_non_stream(messages, memory, tool_round=0, allow_tools=True)
    
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
        full_text = ""
        chunk_id = None
        sent_length = 0
        suppress_stream = False
        
        stream = await self._model(messages)
        async for chunk in stream:
            if chunk_id is None:
                chunk_id = getattr(chunk, "id", None)
            
            for block in chunk.content:
                if block["type"] == "text":
                    full_text = block["text"]
                    if allow_tools and self._looks_like_tool_call(full_text):
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
