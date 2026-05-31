from .base_tool import BaseTool
from .calculator_tool import CalculatorTool
from .web_search_tool import WebSearchTool
from .date_tool import DateTool
from .weather_tool import WeatherTool


__all__ = ["BaseTool", "CalculatorTool", "WebSearchTool", "DateTool", "WeatherTool"]

tool_registry = {
    "calculator": CalculatorTool,
    "web_search": WebSearchTool,
    "date_tool": DateTool,
    "weather_tool": WeatherTool,
}
