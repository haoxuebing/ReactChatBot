from typing import List, Dict, Any
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg


class InMemoryBackend:
    """基于AgentScope InMemoryMemory的记忆后端实现"""
    
    def __init__(self):
        self._memory = InMemoryMemory()
        self._message_count = 0
    
    async def get_history(self) -> List[Dict[str, Any]]:
        """获取历史对话记录"""
        history = await self._memory.get_memory()
        return [{"role": h.role, "content": h.content} for h in history]
    
    async def add_messages(self, messages: List[Dict[str, Any]]) -> None:
        """添加消息到记忆中"""
        msgs = [Msg(name=m["role"], role=m["role"], content=m["content"]) for m in messages]
        await self._memory.add(msgs)
        self._message_count += len(msgs)
    
    async def clear(self) -> None:
        """清空记忆"""
        self._memory.clear_memory()
        self._message_count = 0
    
    def get_message_count(self) -> int:
        """获取消息数量"""
        return self._message_count
