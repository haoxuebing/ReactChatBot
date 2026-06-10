import logging
import json
from pathlib import Path
from typing import Any

from agentscope.mcp import HttpMCPConfig

from .project_client import ProjectMCPClient

logger = logging.getLogger(__name__)

DEFAULT_MCP_CONFIG_PATH = Path(__file__).resolve().parents[2] / "mcp.json"


def _infer_server_kind(server_name: str, configured_kind: str | None) -> str:
    if configured_kind:
        return configured_kind

    normalized = server_name.lower()
    if "hotel" in normalized:
        return "hotel"
    if "12306" in normalized:
        return "12306"
    return server_name


def _load_mcp_servers(config_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(config_path)
    if not path.exists():
        logger.info("MCP 配置文件不存在，跳过自动注册: %s", path)
        return {}

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    servers = payload.get("mcpServers", {})
    if not isinstance(servers, dict):
        logger.warning("MCP 配置中的 mcpServers 不是对象，跳过自动注册: %s", path)
        return {}
    return servers


def build_mcp_clients(
    config_path: str | Path = DEFAULT_MCP_CONFIG_PATH,
) -> list[ProjectMCPClient]:
    """根据 mcp.json 自动构建 MCP 客户端（AgentScope 2.0 Stateless HTTP）。"""
    clients: list[ProjectMCPClient] = []

    for server_key, cfg in _load_mcp_servers(config_path).items():
        server_type = str(cfg.get("type", "")).strip()
        if server_type != "streamable_http":
            logger.warning(
                "MCP [%s] 类型 %s 暂不支持，已跳过",
                server_key,
                server_type or "<empty>",
            )
            continue

        url = str(cfg.get("url", "")).strip()
        if not url:
            logger.warning("MCP [%s] 缺少 url，已跳过", server_key)
            continue

        name = str(cfg.get("name") or server_key)
        headers = cfg.get("headers") or None
        execution_timeout = float(cfg.get("execution_timeout", 120.0))

        clients.append(
            ProjectMCPClient(
                name=name,
                server_kind=_infer_server_kind(name, cfg.get("server_kind")),
                is_stateful=False,
                mcp_config=HttpMCPConfig(url=url, headers=headers),
                execution_timeout=execution_timeout,
            ),
        )
        logger.info(
            "已注册 MCP [%s] kind=%s url=%s",
            name,
            _infer_server_kind(name, cfg.get("server_kind")),
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
