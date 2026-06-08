import asyncio

from agentscope.message import TextBlock
from agentscope.tool import ToolChunk

from .base_tool import SimpleToolBase
from .qweather_client import get_weather


class WeatherTool(SimpleToolBase):
    """国内城市天气查询工具（和风天气 API）"""

    name = "weather_tool"
    description = (
        "查询中国国内城市的实时天气与逐日预报（数据来源：和风天气）。"
        "查天气时必须使用此工具，不要用 web_search。"
        "若用户问明天/后天，先用 date_tool 算出 YYYY-MM-DD，再传入 date 参数。"
    )
    input_schema = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市或区县名称，如「北京」「上海」「杭州」",
            },
            "date": {
                "type": "string",
                "description": (
                    "可选，目标日期 YYYY-MM-DD；省略则返回实时天气及未来7天预报"
                ),
            },
            "adm": {
                "type": "string",
                "description": "可选，上级行政区，用于消歧，如「陕西」",
            },
        },
        "required": ["city"],
    }

    async def __call__(
        self,
        city: str,
        date: str | None = None,
        adm: str | None = None,
    ) -> ToolChunk:
        city = (city or "").strip()
        if not city:
            return ToolChunk(content=[TextBlock(text="错误：请提供城市名称")])

        date_str = (date or "").strip() or None
        adm_str = (adm or "").strip() or None

        try:
            result = await asyncio.to_thread(get_weather, city, date_str, adm_str)
            return ToolChunk(content=[TextBlock(text=result)])
        except Exception as e:
            return ToolChunk(content=[TextBlock(text=f"天气查询失败：{e}")])
