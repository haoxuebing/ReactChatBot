import logging
from typing import Any

import httpx
from agentscope.message import TextBlock, ToolResultState
from agentscope.permission import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
)
from agentscope.tool import MCPTool, ToolChunk

from ..mcp_result_formatter import format_mcp_tool_result, normalize_mcp_args

logger = logging.getLogger(__name__)


class EnhancedMCPTool(MCPTool):
    """在 AgentScope MCPTool 之上增加参数归一化与结果格式化。"""

    def __init__(self, *args: Any, server_kind: str = "generic", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.server_kind = server_kind

    @property
    def original_tool_name(self) -> str:
        return self._tool.name

    async def check_permissions(
        self,
        tool_input: dict[str, Any],
        context: PermissionContext,
    ) -> PermissionDecision:
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message=f"MCP tool {self.original_tool_name} allowed.",
        )

    def _normalize_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if self.server_kind == "hotel":
            return normalize_mcp_args(self.original_tool_name, kwargs)
        return kwargs

    def _format_text(self, text: str) -> str:
        if self.server_kind == "hotel":
            return format_mcp_tool_result(self.original_tool_name, text)
        if self.server_kind == "12306":
            return format_mcp_tool_result(self.original_tool_name, text, max_chars=8000)
        return format_mcp_tool_result(self.original_tool_name, text)

    def _error_chunk(self, message: str) -> ToolChunk:
        return ToolChunk(
            content=[TextBlock(text=message)],
            state=ToolResultState.ERROR,
        )

    async def __call__(self, **kwargs: Any) -> ToolChunk:
        normalized = self._normalize_kwargs(kwargs)
        try:
            chunk = await super().__call__(**normalized)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning(
                "MCP [%s] tool %s HTTP %s",
                self.mcp_name,
                self.original_tool_name,
                status,
            )
            return self._error_chunk(
                f"MCP 服务调用失败（HTTP {status}）：{self.mcp_name} 暂时不可用，"
                "请稍后重试或换一种方式查询。",
            )
        except httpx.RequestError as exc:
            logger.warning(
                "MCP [%s] tool %s request failed: %s",
                self.mcp_name,
                self.original_tool_name,
                exc,
            )
            return self._error_chunk(
                f"MCP 服务连接失败：{self.mcp_name} 无法访问，请检查网络或稍后重试。",
            )
        except Exception:
            logger.exception(
                "MCP [%s] tool %s unexpected error",
                self.mcp_name,
                self.original_tool_name,
            )
            return self._error_chunk(
                f"MCP 工具 {self.original_tool_name} 调用异常，请稍后重试。",
            )

        formatted_blocks = []
        for block in chunk.content:
            if isinstance(block, TextBlock):
                formatted_blocks.append(
                    TextBlock(text=self._format_text(block.text)),
                )
            else:
                formatted_blocks.append(block)

        return ToolChunk(content=formatted_blocks, state=chunk.state)
