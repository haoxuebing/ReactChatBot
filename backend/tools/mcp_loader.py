import logging
import os

from agentscope.mcp import HttpStatelessClient

from .mcp_tool_adapter import MCPToolAdapter

logger = logging.getLogger(__name__)


async def load_mcp_tools() -> dict[str, MCPToolAdapter]:
    """从环境变量加载 MCP 服务并返回工具字典。"""
    tools: dict[str, MCPToolAdapter] = {}

    url = os.getenv("MCP_12306_URL", "").strip()
    if not url:
        logger.info("MCP_12306_URL 未配置，跳过 12306 MCP")
        return tools

    client = HttpStatelessClient(
        name="12306-mcp",
        transport="streamable_http",
        url=url,
    )

    mcp_tools = await client.list_tools()
    for tool_info in mcp_tools:
        func = await client.get_callable_function(
            func_name=tool_info.name,
            wrap_tool_result=True,
        )
        adapter = MCPToolAdapter(func)
        tools[adapter.name] = adapter

    logger.info("12306 MCP 已加载 %d 个工具: %s", len(tools), list(tools.keys()))
    return tools
