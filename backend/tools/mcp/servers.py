from dataclasses import dataclass


@dataclass(frozen=True)
class MCPServerConfig:
    """单个 MCP 服务的配置。"""

    env_key: str
    name: str
    server_kind: str
    description: str
    execution_timeout: float = 120.0


MCP_SERVERS: tuple[MCPServerConfig, ...] = (
    MCPServerConfig(
        env_key="MCP_12306_URL",
        name="12306_mcp",
        server_kind="12306",
        description="12306 火车票/车次/车站查询（ModelScope Streamable HTTP）",
        execution_timeout=90.0,
    ),
    MCPServerConfig(
        env_key="MCP_HOTEL_URL",
        name="hotel_mcp",
        server_kind="hotel",
        description="全球酒店搜索、价格与房型查询（ModelScope Streamable HTTP）",
        execution_timeout=120.0,
    ),
)
