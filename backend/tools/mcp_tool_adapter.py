from typing import Any

from .base_tool import BaseTool
from .mcp_result_formatter import format_mcp_tool_result, normalize_mcp_args


def extract_mcp_result_text(result: Any) -> str:
    if hasattr(result, "content"):
        parts = []
        for block in result.content or []:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        text = "".join(parts)
        return text if text else str(result)
    return str(result)


class MCPToolAdapter(BaseTool):
    """将 AgentScope MCP 可调用函数适配为 BaseTool。"""

    def __init__(self, func_obj: Any):
        self._func = func_obj
        schema = func_obj.json_schema["function"]
        self.name = schema["name"]
        self.description = schema.get("description", "")
        params = schema.get("parameters", {})
        if params.get("type") == "object":
            self._full_parameters = params
            self.parameters = params.get("properties", {})
        else:
            self._full_parameters = {"type": "object", "properties": params}
            self.parameters = params

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._full_parameters,
            },
        }

    async def execute(self, **kwargs) -> str:
        normalized = normalize_mcp_args(self.name, kwargs)
        result = await self._func(**normalized)
        text = extract_mcp_result_text(result)
        return format_mcp_tool_result(self.name, text)
