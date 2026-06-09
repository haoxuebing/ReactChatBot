import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """你是一个对话摘要助手。请将给定对话压缩为简洁的中文摘要，保留：
- 用户的关键问题、偏好、约束条件（如日期、地点、姓名等）
- 已达成的重要结论和事实
- 未解决的问题

要求：使用第三人称客观叙述，200-400 字，不要用 Markdown 标题，不要编造对话中没有的信息。"""

MAX_SUMMARY_SOURCE_CHARS = 12000


def split_history_by_rounds(
    history: list[Dict[str, Any]],
    round_limit: int,
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    """将历史拆分为 (早期历史, 最近 N 轮完整对话)。"""
    if round_limit <= 0 or not history:
        return [], []

    assistant_indices = [
        i for i, msg in enumerate(history) if msg.get("role") == "assistant"
    ]
    if len(assistant_indices) <= round_limit:
        return [], list(history)

    cut_index = assistant_indices[-round_limit]
    start = cut_index
    while start > 0 and history[start - 1].get("role") == "user":
        start -= 1
    return list(history[:start]), list(history[start:])


def _format_messages_for_summary(messages: list[Dict[str, Any]]) -> str:
    lines: list[str] = []
    total_chars = 0
    for msg in messages:
        role_label = "用户" if msg.get("role") == "user" else "助手"
        content = str(msg.get("content", ""))
        remaining = MAX_SUMMARY_SOURCE_CHARS - total_chars
        if remaining <= 0:
            lines.append("…（后续对话已省略）")
            break
        if len(content) > remaining:
            content = content[:remaining] + "…（已截断）"
        lines.append(f"{role_label}：{content}")
        total_chars += len(content)
    return "\n".join(lines)


def _extract_response_text(response: Any) -> str:
    parts: list[str] = []
    for block in response.content:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        elif hasattr(block, "text"):
            parts.append(str(block.text))
    return "".join(parts).strip()


async def summarize_history(
    model: Callable[..., Any],
    messages: list[Dict[str, Any]],
    existing_summary: Optional[str] = None,
) -> str:
    """调用大模型生成或增量更新历史摘要。"""
    conversation = _format_messages_for_summary(messages)
    if not conversation.strip():
        return existing_summary or ""

    if existing_summary:
        user_content = (
            f"已有历史摘要：\n{existing_summary}\n\n"
            f"以下为新发生的对话，请合并更新摘要：\n{conversation}"
        )
    else:
        user_content = f"请摘要以下对话：\n{conversation}"

    response = await model(
        [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        stream=False,
    )
    summary = _extract_response_text(response)
    if not summary:
        raise ValueError("empty summary response")
    return summary


def build_summary_system_message(summary: str) -> Dict[str, str]:
    return {
        "role": "system",
        "content": f"【早期对话摘要】\n{summary}",
    }
