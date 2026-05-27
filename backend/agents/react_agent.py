import json
import re
from typing import List, Dict, Any, AsyncGenerator, Optional

from agentscope.model import OpenAIChatModel

from tools import tool_registry, BaseTool
from memory.in_memory_backend import InMemoryBackend


class ReActAgent:
    """ReAct智能体，实现思考-行动循环"""
    
    def __init__(self, model: OpenAIChatModel):
        self._model = model
        self._tools = {name: cls() for name, cls in tool_registry.items()}
    
    @property
    def tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具的描述"""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def _extract_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """从模型响应中提取工具调用"""
        try:
            # 尝试匹配JSON格式的工具调用
            match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 尝试直接解析JSON
            return json.loads(content)
        except:
            return None
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具调用"""
        if tool_name not in self._tools:
            return f"错误：未知工具 '{tool_name}'"
        
        tool: BaseTool = self._tools[tool_name]
        try:
            result = await tool.execute(**arguments)
            return result
        except Exception as e:
            return f"工具执行错误：{str(e)}"
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        memory: Optional[InMemoryBackend] = None,
        stream: bool = False,
    ) -> Any:
        """执行聊天逻辑，支持工具调用"""
        # 如果有工具，添加工具描述到系统消息
        if self._tools:
            tools_desc = json.dumps(self.tools, ensure_ascii=False)
            tool_prompt = f"""你可以使用以下工具来帮助回答问题：
{tools_desc}

如果需要调用工具，请使用JSON格式输出，例如：
```json
{{"name": "工具名称", "arguments": {{"参数名": "参数值"}}}}
```

如果直接回答问题，请直接输出内容，不需要使用JSON格式。"""
            
            # 查找或创建系统消息
            system_msg_exists = any(m["role"] == "system" for m in messages)
            if system_msg_exists:
                for m in messages:
                    if m["role"] == "system":
                        m["content"] += "\n\n" + tool_prompt
                        break
            else:
                messages.insert(0, {"role": "system", "content": tool_prompt})
        
        if stream:
            return self._chat_stream(messages, memory)
        else:
            return await self._chat_non_stream(messages, memory)
    
    async def _chat_non_stream(self, messages: List[Dict[str, Any]], memory: Optional[InMemoryBackend]) -> Dict[str, Any]:
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
        
        # 检查是否需要调用工具
        tool_call = self._extract_tool_call(full_text)
        if tool_call and "name" in tool_call:
            # 执行工具调用
            tool_result = await self._execute_tool(
                tool_call["name"],
                tool_call.get("arguments", {})
            )
            
            # 将工具结果作为系统消息添加到对话中
            messages.append({
                "role": "system",
                "content": f"工具执行结果：\n{tool_result}"
            })
            
            # 再次调用模型进行总结
            return await self._chat_non_stream(messages, memory)
        
        return {
            "id": first_chunk_id,
            "object": "chat.completion",
            "created": 0,
            "model": self._model.model_name,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": full_text},
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
        memory: Optional[InMemoryBackend]
    ) -> AsyncGenerator[str, None]:
        """流式聊天"""
        full_text = ""
        chunk_id = None
        
        stream = await self._model(messages)
        async for chunk in stream:
            if chunk_id is None:
                chunk_id = getattr(chunk, "id", None)
            
            for block in chunk.content:
                if block["type"] == "text":
                    # 计算增量文本（只返回新增的部分）
                    delta = block["text"][len(full_text):]
                    full_text = block["text"]
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
        
        # 检查是否需要调用工具
        tool_call = self._extract_tool_call(full_text)
        if tool_call and "name" in tool_call:
            # 发送思考信息
            yield {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": 0,
                "model": self._model.model_name,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": "",
                        "thinking": f"我需要调用工具来获取信息。用户的问题需要使用 {tool_call['name']} 工具来回答。"
                    },
                    "finish_reason": None
                }]
            }
            
            # 执行工具调用
            tool_result = await self._execute_tool(
                tool_call["name"],
                tool_call.get("arguments", {})
            )
            
            # 发送工具调用信息
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
            
            # 将工具结果作为系统消息添加到对话中
            messages.append({
                "role": "system",
                "content": f"工具执行结果：\n{tool_result}"
            })
            
            # 再次调用模型进行总结
            async for response in self._chat_stream(messages, memory):
                yield response
            return
        
        # 结束标记
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
