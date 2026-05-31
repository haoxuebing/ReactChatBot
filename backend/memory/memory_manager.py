import uuid
from typing import Dict, Any, Optional

from .in_memory_backend import InMemoryBackend


def normalize_username(username: Optional[str]) -> str:
    return (username or "").strip()[:12]


class MemoryManager:
    """记忆管理器，负责会话级别的记忆管理"""

    def __init__(self):
        self._sessions: Dict[str, InMemoryBackend] = {}
        self._session_usernames: Dict[str, str] = {}
        self._usernames: set[str] = set()

    def register_username(self, username: str) -> str:
        """注册用户名，已存在则直接返回"""
        normalized = normalize_username(username)
        if not normalized:
            raise ValueError("用户名不能为空")
        self._usernames.add(normalized)
        return normalized

    def list_usernames(self) -> list[str]:
        """获取所有已注册用户名"""
        return sorted(self._usernames)

    def get_user_session_ids(self, username: str) -> list[str]:
        """获取指定用户名下的所有 session_id"""
        normalized = normalize_username(username)
        if normalized not in self._usernames:
            return []
        return [
            session_id
            for session_id, owner in self._session_usernames.items()
            if owner == normalized
        ]

    def bind_session(self, username: str, session_id: str) -> None:
        """将 session_id 绑定到用户名"""
        normalized = normalize_username(username)
        if not normalized:
            raise ValueError("用户名不能为空")
        self.register_username(normalized)
        self._session_usernames[session_id] = normalized

    def get_session_username(self, session_id: str) -> Optional[str]:
        return self._session_usernames.get(session_id)

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> tuple[str, InMemoryBackend]:
        """获取或创建会话记忆"""
        if session_id and session_id in self._sessions:
            if username:
                self.bind_session(username, session_id)
            return session_id, self._sessions[session_id]

        new_id = session_id or uuid.uuid4().hex[:12]
        self._sessions[new_id] = InMemoryBackend()
        if username:
            self.bind_session(username, new_id)
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

    async def _build_session_summary(
        self,
        session_id: str,
        backend: InMemoryBackend,
    ) -> Dict[str, Any]:
        history = await backend.get_history()
        first_user = next((m for m in history if m["role"] == "user"), None)
        last_msg = history[-1] if history else None

        name = "未命名会话"
        if first_user and first_user.get("content"):
            content = first_user["content"]
            name = content[:20] + ("..." if len(content) > 20 else "")

        last_message = ""
        if last_msg and last_msg.get("content"):
            content = last_msg["content"]
            last_message = content[:30] + ("..." if len(content) > 30 else "")

        return {
            "session_id": session_id,
            "username": self._session_usernames.get(session_id),
            "message_count": backend.get_message_count(),
            "name": name,
            "last_message": last_message,
        }

    async def list_sessions(self, username: Optional[str] = None) -> list[Dict[str, Any]]:
        """获取会话列表，可按用户名过滤"""
        normalized = normalize_username(username) if username else ""
        result = []
        for session_id, backend in self._sessions.items():
            owner = self._session_usernames.get(session_id)
            if normalized and owner != normalized:
                continue
            result.append(await self._build_session_summary(session_id, backend))
        return result

    async def list_user_sessions(self, username: str) -> list[Dict[str, Any]]:
        """获取指定用户名下的会话详情列表"""
        normalized = normalize_username(username)
        if normalized not in self._usernames:
            return []

        result = []
        for session_id in self.get_user_session_ids(normalized):
            backend = self._sessions.get(session_id)
            if not backend:
                continue
            summary = await self._build_session_summary(session_id, backend)
            result.append(summary)
        return result

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """获取指定会话的详细信息（包含对话内容）"""
        backend = self._sessions.get(session_id)
        if not backend:
            return {"error": f"Session '{session_id}' not found"}

        history = await backend.get_history()
        return {
            "session_id": session_id,
            "username": self._session_usernames.get(session_id),
            "message_count": backend.get_message_count(),
            "messages": history,
        }

    def delete_session(self, session_id: str) -> bool:
        """删除指定会话，存在则删除并返回 True，否则返回 False"""
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        self._session_usernames.pop(session_id, None)
        return True
