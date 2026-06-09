import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .file_backend import FileBackend
from .history_summary import (
    build_summary_system_message,
    split_history_by_rounds,
    summarize_history,
)

logger = logging.getLogger(__name__)


def _message_for_llm(msg: Dict[str, Any]) -> Dict[str, str]:
    """仅保留模型所需字段，忽略 timestamp 等元数据"""
    return {"role": msg["role"], "content": msg["content"]}


def _format_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _stamp_message(
    msg: Dict[str, Any],
    timestamp: str,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    stamped: Dict[str, Any] = {
        "role": msg["role"],
        "content": msg["content"],
        "timestamp": timestamp,
    }
    if msg["role"] == "user" and client_ip:
        stamped["ip"] = client_ip
    return stamped


def normalize_username(username: Optional[str]) -> str:
    return (username or "").strip()[:12]


class MemoryManager:
    """记忆管理器，负责会话级别的记忆管理（文件持久化）"""

    def __init__(
        self,
        data_dir: str | Path | None = None,
        memory_round_limit: int = 20,
        summary_enabled: bool = True,
        summary_model: Callable[..., Any] | None = None,
    ):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data" / "chat_memory"
        self._memory_round_limit = max(0, memory_round_limit)
        self._summary_enabled = summary_enabled
        self._summary_model = summary_model
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._sessions_dir = self._data_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._data_dir / "index.json"
        self._sessions: Dict[str, FileBackend] = {}
        self._session_usernames: Dict[str, str] = {}
        self._deleted_sessions: set[str] = set()
        self._usernames: set[str] = set()
        self._load_index()

    def _load_index(self) -> None:
        if not self._index_path.exists():
            return
        with open(self._index_path, encoding="utf-8") as f:
            data = json.load(f)
        self._usernames = set(data.get("usernames", []))
        self._session_usernames = dict(data.get("session_usernames", {}))
        self._deleted_sessions = set(data.get("deleted_sessions", []))

    def _save_index(self) -> None:
        payload = {
            "usernames": sorted(self._usernames),
            "session_usernames": self._session_usernames,
            "deleted_sessions": sorted(self._deleted_sessions),
        }
        tmp_path = self._index_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp_path.replace(self._index_path)

    def _session_file_exists(self, session_id: str) -> bool:
        return (self._sessions_dir / f"{session_id}.json").exists()

    def _is_deleted(self, session_id: str) -> bool:
        return session_id in self._deleted_sessions

    def _get_backend(self, session_id: str) -> FileBackend:
        if session_id not in self._sessions:
            self._sessions[session_id] = FileBackend(session_id, self._data_dir)
        return self._sessions[session_id]

    def _iter_session_ids(self) -> set[str]:
        ids = set(self._session_usernames.keys())
        for path in self._sessions_dir.glob("*.json"):
            ids.add(path.stem)
        return {sid for sid in ids if not self._is_deleted(sid)}

    def register_username(self, username: str) -> str:
        """注册用户名，已存在则直接返回"""
        normalized = normalize_username(username)
        if not normalized:
            raise ValueError("用户名不能为空")
        self._usernames.add(normalized)
        self._save_index()
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
            if owner == normalized and not self._is_deleted(session_id)
        ]

    def bind_session(self, username: str, session_id: str) -> None:
        """将 session_id 绑定到用户名"""
        normalized = normalize_username(username)
        if not normalized:
            raise ValueError("用户名不能为空")
        self.register_username(normalized)
        self._session_usernames[session_id] = normalized
        self._save_index()

    def get_session_username(self, session_id: str) -> Optional[str]:
        return self._session_usernames.get(session_id)

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> tuple[str, FileBackend]:
        """获取或创建会话记忆"""
        if session_id and self._is_deleted(session_id):
            session_id = None
        if session_id and (
            session_id in self._sessions or self._session_file_exists(session_id)
        ):
            if username:
                self.bind_session(username, session_id)
            return session_id, self._get_backend(session_id)

        new_id = session_id or uuid.uuid4().hex[:12]
        self._sessions[new_id] = FileBackend(new_id, self._data_dir)
        if username:
            self.bind_session(username, new_id)
        return new_id, self._sessions[new_id]

    async def _resolve_history_summary(
        self,
        backend: FileBackend,
        history: list[Dict[str, Any]],
        cut_start: int,
    ) -> str | None:
        if cut_start <= 0:
            return None
        if not self._summary_enabled or self._summary_model is None:
            return None

        cached = await backend.get_history_summary()
        try:
            if cached and cached["covers_until_index"] == cut_start:
                return cached["content"]

            if cached and cached["covers_until_index"] < cut_start:
                messages_to_summarize = history[cached["covers_until_index"]:cut_start]
                summary = await summarize_history(
                    self._summary_model,
                    messages_to_summarize,
                    existing_summary=cached["content"],
                )
            else:
                summary = await summarize_history(
                    self._summary_model,
                    history[:cut_start],
                )

            await backend.set_history_summary(summary, cut_start)
            return summary
        except Exception:
            logger.exception("历史摘要生成失败，将仅使用最近完整对话")
            return None

    async def build_messages_with_history(
        self,
        backend: FileBackend,
        new_messages: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        """构建注入模型的消息：早期摘要 + 最近 N 轮完整对话 + 本次新消息。"""
        history = await backend.get_history()
        early_history, recent_history = split_history_by_rounds(
            history,
            self._memory_round_limit,
        )
        result: list[Dict[str, str]] = []

        summary = await self._resolve_history_summary(
            backend,
            history,
            len(early_history),
        )
        if summary:
            result.append(build_summary_system_message(summary))

        result.extend(_message_for_llm(m) for m in recent_history)
        result.extend(_message_for_llm(m) for m in new_messages)
        return result

    async def save_to_memory(
        self,
        backend: FileBackend,
        user_messages: list[Dict[str, Any]],
        assistant_content: str,
        client_ip: Optional[str] = None,
    ) -> None:
        """保存对话到记忆"""
        base = datetime.now()
        messages_to_save = []
        for i, msg in enumerate(user_messages):
            ts = _format_timestamp(base + timedelta(seconds=i))
            messages_to_save.append(_stamp_message(msg, ts, client_ip))
        messages_to_save.append(
            _stamp_message(
                {"role": "assistant", "content": assistant_content},
                _format_timestamp(base + timedelta(seconds=len(user_messages))),
            )
        )
        await backend.add_messages(messages_to_save)

    async def _build_session_summary(
        self,
        session_id: str,
        backend: FileBackend,
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
        for session_id in sorted(self._iter_session_ids()):
            owner = self._session_usernames.get(session_id)
            if normalized and owner != normalized:
                continue
            backend = self._get_backend(session_id)
            result.append(await self._build_session_summary(session_id, backend))
        return result

    async def list_user_sessions(self, username: str) -> list[Dict[str, Any]]:
        """获取指定用户名下的会话详情列表"""
        normalized = normalize_username(username)
        if normalized not in self._usernames:
            return []

        result = []
        for session_id in self.get_user_session_ids(normalized):
            backend = self._get_backend(session_id)
            summary = await self._build_session_summary(session_id, backend)
            result.append(summary)
        return result

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """获取指定会话的详细信息（包含对话内容）"""
        if self._is_deleted(session_id):
            return {"error": f"Session '{session_id}' not found"}
        if not self._session_file_exists(session_id) and session_id not in self._sessions:
            return {"error": f"Session '{session_id}' not found"}

        backend = self._get_backend(session_id)
        history = await backend.get_history()
        return {
            "session_id": session_id,
            "username": self._session_usernames.get(session_id),
            "message_count": backend.get_message_count(),
            "messages": history,
        }

    def _sanitize_messages_for_share(
        self, messages: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """分享视图：移除 IP 等敏感字段，仅保留展示所需内容"""
        sanitized = []
        for msg in messages:
            item: Dict[str, Any] = {
                "role": msg["role"],
                "content": msg["content"],
            }
            if msg.get("timestamp"):
                item["timestamp"] = msg["timestamp"]
            sanitized.append(item)
        return sanitized

    async def get_session_for_share(self, session_id: str) -> Dict[str, Any]:
        """获取用于公开分享的会话（脱敏，不含用户名与 IP）"""
        if self._is_deleted(session_id):
            return {"error": f"Session '{session_id}' not found"}
        if not self._session_file_exists(session_id) and session_id not in self._sessions:
            return {"error": f"Session '{session_id}' not found"}

        backend = self._get_backend(session_id)
        history = await backend.get_history()
        if not history:
            return {"error": "Session has no messages to share"}

        summary = await self._build_session_summary(session_id, backend)
        return {
            "session_id": session_id,
            "name": summary["name"],
            "message_count": backend.get_message_count(),
            "messages": self._sanitize_messages_for_share(history),
        }

    def delete_session(self, session_id: str) -> bool:
        """软删除指定会话（保留文件，仅从列表隐藏）"""
        if self._is_deleted(session_id):
            return True
        exists = session_id in self._sessions or self._session_file_exists(session_id)
        if not exists and session_id not in self._session_usernames:
            return False

        self._deleted_sessions.add(session_id)
        self._sessions.pop(session_id, None)
        self._save_index()
        return True
