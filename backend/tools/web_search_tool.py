import asyncio

from .base_tool import BaseTool
from .bing_client import search_with_content


def _format_results(query: str, results) -> str:
    lines = [f"搜索 '{query}' 的结果（必应中文）：\n"]
    for i, r in enumerate(results, start=1):
        block = f"{i}. {r.title}\n摘要: {r.snippet}\n链接: {r.url}"
        if r.page_content:
            block += f"\n正文摘录:\n{r.page_content}"
        lines.append(block)
    return "\n\n".join(lines)


class WebSearchTool(BaseTool):
    """网络搜索工具，使用必应中文搜索引擎"""

    name = "web_search"
    description = (
        "使用必应中文搜索引擎获取互联网最新信息。"
        "天气查询请使用 weather_tool，不要用本工具。"
        "新闻类建议加上年份等具体关键词，如「2026 最新 ...」。"
    )
    parameters = {
        "query": {
            "type": "string",
            "description": "搜索关键词",
        }
    }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        if not query:
            return "错误：请提供搜索关键词"

        try:
            results = await asyncio.to_thread(search_with_content, query, 5, 2)
            if not results:
                return f"搜索 '{query}' 未找到相关结果"
            return _format_results(query, results)
        except Exception as e:
            return f"搜索失败：{str(e)}"
