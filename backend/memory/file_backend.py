import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List


class FileBackend:
    """基于 JSON 文件的记忆后端，每个会话对应一个文件"""

    def __init__(self, session_id: str, data_dir: Path):
        self._session_id = session_id
        self._sessions_dir = data_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = self._sessions_dir / f"{session_id}.json"
        self._lock = Lock()

    def _read_data(self) -> Dict[str, Any]:
        if not self._file_path.exists():
            return {"messages": [], "message_count": 0}
        with open(self._file_path, encoding="utf-8") as f:
            return json.load(f)

    def _write_data(self, data: Dict[str, Any]) -> None:
        tmp_path = self._file_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(self._file_path)

    async def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read_data()
        return list(data.get("messages", []))

    async def get_history_summary(self) -> Dict[str, Any] | None:
        with self._lock:
            data = self._read_data()
        summary = data.get("history_summary")
        if not isinstance(summary, dict):
            return None
        content = summary.get("content")
        covers_until_index = summary.get("covers_until_index")
        if not content or not isinstance(covers_until_index, int):
            return None
        return {
            "content": str(content),
            "covers_until_index": covers_until_index,
        }

    async def set_history_summary(
        self,
        content: str,
        covers_until_index: int,
    ) -> None:
        with self._lock:
            data = self._read_data()
            data["history_summary"] = {
                "content": content,
                "covers_until_index": covers_until_index,
            }
            self._write_data(data)

    async def add_messages(self, messages: List[Dict[str, Any]]) -> None:
        with self._lock:
            data = self._read_data()
            stored = data.setdefault("messages", [])
            stored.extend(messages)
            data["message_count"] = len(stored)
            self._write_data(data)

    async def clear(self) -> None:
        with self._lock:
            self._write_data({"messages": [], "message_count": 0})

    def get_message_count(self) -> int:
        with self._lock:
            data = self._read_data()
        return int(data.get("message_count", len(data.get("messages", []))))

    def delete_file(self) -> bool:
        """删除会话文件，存在则返回 True"""
        with self._lock:
            if not self._file_path.exists():
                return False
            self._file_path.unlink()
            return True
