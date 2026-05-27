import uuid
from typing import Dict, Any, Optional

from .in_memory_backend import InMemoryBackend


class MemoryManager:
    """记忆管理器，负责会话级别的记忆管理"""
    
    def __init__(self):
        self._sessions: Dict[str, InMemoryBackend] = {}
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> tuple[str, InMemoryBackend]:
        """获取或创建会话记忆"""
        if session_id and session_id in self._sessions:
            return session_id, self._sessions[session_id]
        
        new_id = session_id or uuid.uuid4().hex[:12]
        self._sessions[new_id] = InMemoryBackend()
        return new_id, self._sessions[new_id]
    
    async def build_messages_with_history(
        self,
        backend: InMemoryBackend,
        new_messages: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        """构建包含历史记录的完整消息列表"""
        history = await backend.get_history()
        result = []
        result.extend(history)
        result.extend(new_messages)
        return result
    
    async def save_to_memory(
        self,
        backend: InMemoryBackend,
        user_messages: list[Dict[str, Any]],
        assistant_content: str,
    ) -> None:
        """保存对话到记忆"""
        messages_to_save = []
        messages_to_save.extend(user_messages)
        messages_to_save.append({"role": "assistant", "content": assistant_content})
        await backend.add_messages(messages_to_save)
    
    def list_sessions(self) -> list[Dict[str, Any]]:
        """获取所有会话列表"""
        return [
            {"session_id": session_id, "message_count": backend.get_message_count()}
            for session_id, backend in self._sessions.items()
        ]
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """获取指定会话的详细信息（包含对话内容）"""
        backend = self._sessions.get(session_id)
        if not backend:
            return {"error": f"Session '{session_id}' not found"}
        
        history = await backend.get_history()
        return {
            "session_id": session_id,
            "message_count": backend.get_message_count(),
            "messages": history,
        }
