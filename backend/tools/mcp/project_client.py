import mcp.types
from pydantic import Field

from agentscope.mcp import MCPClient

from .enhanced_tool import EnhancedMCPTool


class ProjectMCPClient(MCPClient):
    """项目 MCP 客户端：返回带业务增强的 EnhancedMCPTool。"""

    server_kind: str = Field(
        default="generic",
        description="业务类型：12306 / hotel / generic",
    )

    def _filter_cached_tools(
        self,
        tools: list[mcp.types.Tool],
    ) -> list[mcp.types.Tool]:
        available = tools
        if self.enable_tools is not None:
            available = [tool for tool in available if tool.name in self.enable_tools]
        if self.disable_tools is not None:
            available = [
                tool for tool in available if tool.name not in self.disable_tools
            ]
        return available

    async def list_raw_tools(self) -> list[mcp.types.Tool]:
        """复用已缓存的工具列表，避免 stateless 模式下重复建立 MCP 连接。"""
        if self._cached_tools is not None:
            return self._filter_cached_tools(self._cached_tools)
        return await super().list_raw_tools()

    async def get_tool(self, name: str) -> EnhancedMCPTool:
        if self._cached_tools is None:
            await self.list_raw_tools()

        target_tool = None
        for tool in self._cached_tools or []:
            if tool.name == name:
                target_tool = tool
                break

        if target_tool is None:
            raise ValueError(
                f"Tool '{name}' not found in MCP server '{self.name}'",
            )

        if not self.is_stateful:
            return EnhancedMCPTool(
                server_kind=self.server_kind,
                mcp_name=self.name,
                tool=target_tool,
                client_gen=self._get_client_gen,
                timeout=self.execution_timeout,
            )

        self._validate_connection()
        return EnhancedMCPTool(
            server_kind=self.server_kind,
            mcp_name=self.name,
            tool=target_tool,
            session=self._session,
            timeout=self.execution_timeout,
        )
