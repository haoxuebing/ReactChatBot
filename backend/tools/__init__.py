from .base_tool import BaseTool
from .calculator_tool import CalculatorTool
from .web_search_tool import WebSearchTool
from .date_tool import DateTool


__all__ = ["BaseTool", "CalculatorTool", "WebSearchTool", "DateTool"]

tool_registry = {
    "calculator": CalculatorTool,
    "web_search": WebSearchTool,
    "date_tool": DateTool,
}
