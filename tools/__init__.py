from .base_tool import BaseTool
from .calculator_tool import CalculatorTool
from .web_search_tool import WebSearchTool

__all__ = ["BaseTool", "CalculatorTool", "WebSearchTool"]

tool_registry = {
    "calculator": CalculatorTool,
    "web_search": WebSearchTool,
}
