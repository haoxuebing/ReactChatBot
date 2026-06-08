import logging
import os

from agentscope.mcp import HttpMCPConfig

from .project_client import ProjectMCPClient
from .servers import MCP_SERVERS

logger = logging.getLogger(__name__)


def build_mcp_clients() -> list[ProjectMCPClient]:
    """从环境变量构建 12306 / 酒店 MCP 客户端（AgentScope 2.0 Stateless HTTP）。"""
    clients: list[ProjectMCPClient] = []

    for cfg in MCP_SERVERS:
        url = os.getenv(cfg.env_key, "").strip()
        if not url:
            logger.info("%s 未配置，跳过 %s", cfg.env_key, cfg.name)
            continue

        clients.append(
            ProjectMCPClient(
                name=cfg.name,
                server_kind=cfg.server_kind,
                is_stateful=False,
                mcp_config=HttpMCPConfig(url=url),
                execution_timeout=cfg.execution_timeout,
            ),
        )
        logger.info(
            "已注册 MCP [%s] kind=%s url=%s",
            cfg.name,
            cfg.server_kind,
            url,
        )

    return clients


async def verify_mcp_clients(
    clients: list[ProjectMCPClient],
) -> dict[str, list[str]]:
    """启动时探测 MCP 服务，列出可用工具。"""
    summary: dict[str, list[str]] = {}

    for client in clients:
        try:
            tools = await client.list_raw_tools()
            tool_names = [tool.name for tool in tools]
            summary[client.name] = tool_names
            logger.info(
                "MCP [%s] 连接成功，%d 个工具: %s",
                client.name,
                len(tool_names),
                tool_names,
            )
        except Exception:
            logger.exception("MCP [%s] 连接或列举工具失败", client.name)
            summary[client.name] = []

    return summary
