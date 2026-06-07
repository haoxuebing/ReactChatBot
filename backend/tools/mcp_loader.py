import logging
import os

from agentscope.mcp import HttpStatelessClient

from .mcp_tool_adapter import MCPToolAdapter

logger = logging.getLogger(__name__)

# (环境变量名, MCP 客户端名称)
MCP_SERVER_CONFIGS: list[tuple[str, str]] = [
    ("MCP_12306_URL", "12306-mcp"),
    ("MCP_HOTEL_URL", "hotel-mcp"),
]


async def _load_mcp_server(env_key: str, client_name: str) -> dict[str, MCPToolAdapter]:
    url = os.getenv(env_key, "").strip()
    if not url:
        logger.info("%s 未配置，跳过 %s", env_key, client_name)
        return {}

    client = HttpStatelessClient(
        name=client_name,
        transport="streamable_http",
        url=url,
    )

    tools: dict[str, MCPToolAdapter] = {}
    mcp_tools = await client.list_tools()
    for tool_info in mcp_tools:
        func = await client.get_callable_function(
            func_name=tool_info.name,
            wrap_tool_result=True,
        )
        adapter = MCPToolAdapter(func)
        tools[adapter.name] = adapter

    logger.info(
        "%s 已加载 %d 个工具: %s",
        client_name,
        len(tools),
        list(tools.keys()),
    )
    return tools


async def load_mcp_tools() -> dict[str, MCPToolAdapter]:
    """从环境变量加载所有已配置的 MCP 服务。"""
    tools: dict[str, MCPToolAdapter] = {}

    for env_key, client_name in MCP_SERVER_CONFIGS:
        try:
            server_tools = await _load_mcp_server(env_key, client_name)
            for name, adapter in server_tools.items():
                if name in tools:
                    logger.warning(
                        "MCP 工具名冲突，%s 的 %s 将覆盖已有工具",
                        client_name,
                        name,
                    )
                tools[name] = adapter
        except Exception:
            logger.exception("加载 %s 失败，跳过该 MCP 服务", client_name)

    return tools
