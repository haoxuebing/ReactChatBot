from datetime import datetime, timedelta

from agentscope.message import TextBlock
from agentscope.tool import ToolChunk

from .base_tool import SimpleToolBase


class DateTool(SimpleToolBase):
    """日期工具，提供日期和时间相关功能"""

    name = "date_tool"
    description = "用于获取当前日期时间、日期计算、格式化等日期相关操作"
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": (
                    "操作类型：now(获取当前时间)、format(格式化日期)、"
                    "add(日期加减)、diff(日期差计算)"
                ),
            },
            "date_str": {
                "type": "string",
                "description": (
                    "日期字符串，格式如 '2024-01-15'；"
                    "add 操作时可省略，默认以今天为基准"
                ),
            },
            "format_str": {
                "type": "string",
                "description": "日期格式，如 '%Y-%m-%d'、'%Y年%m月%d日 %H:%M:%S'",
            },
            "days": {
                "type": "integer",
                "description": "加减的天数，正数为加，负数为减",
            },
        },
        "required": ["action"],
    }

    async def __call__(
        self,
        action: str = "now",
        date_str: str | None = None,
        format_str: str | None = None,
        days: int = 0,
    ) -> ToolChunk:
        try:
            if action == "now":
                text = self._get_current_datetime()
            elif action == "format":
                text = self._format_date(date_str, format_str)
            elif action == "add":
                text = self._add_days(date_str, days)
            elif action == "diff":
                text = self._date_diff(date_str, format_str)
            else:
                text = f"错误：未知操作 '{action}'"
        except Exception as e:
            text = f"日期操作失败：{str(e)}"
        return ToolChunk(content=[TextBlock(text=text)])

    def _get_current_datetime(self) -> str:
        now = datetime.now()
        return (
            f"当前日期时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}\n"
            f"日期：{now.strftime('%Y-%m-%d')}\n"
            f"时间：{now.strftime('%H:%M:%S')}\n"
            f"星期：{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}"
        )

    def _format_date(
        self,
        date_str: str | None,
        format_str: str | None,
    ) -> str:
        if not date_str:
            return "错误：请提供日期字符串"
        format_str = format_str or "%Y-%m-%d %H:%M:%S"
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return f"格式化结果：{dt.strftime(format_str)}"
            except ValueError:
                continue
        return f"错误：无法解析日期 '{date_str}'"

    def _add_days(self, date_str: str | None, days: int) -> str:
        if not date_str:
            dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            dt = None
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return f"错误：无法解析日期 '{date_str}'"

        result_dt = dt + timedelta(days=days)
        return (
            f"原日期：{dt.strftime('%Y-%m-%d')}\n"
            f"加减天数：{days} 天\n"
            f"结果日期：{result_dt.strftime('%Y-%m-%d')}\n"
            f"详细信息：{result_dt.strftime('%Y年%m月%d日 %H:%M:%S')}"
        )

    def _date_diff(self, date_str1: str | None, date_str2: str | None) -> str:
        if not date_str1 or not date_str2:
            return "错误：请提供两个日期字符串（date_str 和 format_str）"

        dt1 = dt2 = None
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
            if dt1 is None:
                try:
                    dt1 = datetime.strptime(date_str1, fmt)
                except ValueError:
                    pass
            if dt2 is None:
                try:
                    dt2 = datetime.strptime(date_str2, fmt)
                except ValueError:
                    pass

        if dt1 is None or dt2 is None:
            return "错误：无法解析日期"

        diff = abs((dt1 - dt2).days)
        return (
            f"日期1：{dt1.strftime('%Y-%m-%d')}\n"
            f"日期2：{dt2.strftime('%Y-%m-%d')}\n"
            f"相差天数：{diff} 天"
        )
