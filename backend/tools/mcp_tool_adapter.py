from typing import Any

from .base_tool import BaseTool


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
        self.parameters = params.get("properties", params)

    async def execute(self, **kwargs) -> str:
        result = await self._func(**kwargs)
        return extract_mcp_result_text(result)
