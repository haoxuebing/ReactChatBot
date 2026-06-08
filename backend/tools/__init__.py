from agentscope.tool import Toolkit

from .calculator_tool import CalculatorTool
from .web_search_tool import WebSearchTool
from .date_tool import DateTool
from .weather_tool import WeatherTool
from .mcp import build_mcp_clients, verify_mcp_clients

BUILTIN_TOOLS = [
    CalculatorTool(),
    WebSearchTool(),
    DateTool(),
    WeatherTool(),
]


def build_toolkit(mcp_clients=None) -> Toolkit:
    """构建包含内置工具与 MCP 的 Toolkit。"""
    return Toolkit(
        tools=BUILTIN_TOOLS,
        mcps=mcp_clients or [],
    )
