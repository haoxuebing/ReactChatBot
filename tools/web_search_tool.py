import random
from typing import Any, Dict

from .base_tool import BaseTool


class WebSearchTool(BaseTool):
    """网络搜索工具，模拟搜索功能"""
    
    name = "web_search"
    description = "用于搜索互联网上的最新信息，适用于需要实时数据的问题"
    parameters = {
        "query": {
            "type": "string",
            "description": "搜索关键词"
        }
    }
    
    # 模拟搜索结果
    _mock_results = {
        "天气": "根据最新数据，北京今天晴天，气温25-32°C，空气质量良好",
        "新闻": "今日要闻：人工智能技术取得重大突破，新模型性能提升30%",
        "股票": "上证指数今日收于3200点，较昨日上涨0.5%",
        "科技": "苹果公司发布新款iPhone，搭载A18芯片，性能提升显著",
    }
    
    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        if not query:
            return "错误：请提供搜索关键词"
        
        # 模拟搜索结果
        result = self._mock_results.get(query, None)
        if result:
            return result
        
        # 如果没有预设结果，返回模拟搜索结果
        mock_results = [
            f"搜索结果显示：关于'{query}'的最新信息...",
            f"根据网络搜索，'{query}'相关内容如下：这是模拟搜索结果",
            f"搜索到关于'{query}'的信息：暂无最新数据",
        ]
        return random.choice(mock_results)
