from datetime import datetime, timedelta
from typing import Any, Dict
from .base_tool import BaseTool


class DateTool(BaseTool):
    """日期工具，提供日期和时间相关功能"""
    
    name = "date_tool"
    description = "用于获取当前日期时间、日期计算、格式化等日期相关操作"
    parameters = {
        "action": {
            "type": "string",
            "description": "操作类型：now(获取当前时间)、format(格式化日期)、add(日期加减)、diff(日期差计算)"
        },
        "date_str": {
            "type": "string",
            "description": "日期字符串，格式如 '2024-01-15' 或 '2024-01-15 10:30:00'"
        },
        "format_str": {
            "type": "string",
            "description": "日期格式，如 '%Y-%m-%d'、'%Y年%m月%d日 %H:%M:%S'"
        },
        "days": {
            "type": "integer",
            "description": "加减的天数，正数为加，负数为减"
        }
    }

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action", "now")
        
        try:
            if action == "now":
                return self._get_current_datetime()
            elif action == "format":
                return self._format_date(kwargs)
            elif action == "add":
                return self._add_days(kwargs)
            elif action == "diff":
                return self._date_diff(kwargs)
            else:
                return f"错误：未知操作 '{action}'"
        except Exception as e:
            return f"日期操作失败：{str(e)}"

    def _get_current_datetime(self) -> str:
        now = datetime.now()
        return (
            f"当前日期时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}\n"
            f"日期：{now.strftime('%Y-%m-%d')}\n"
            f"时间：{now.strftime('%H:%M:%S')}\n"
            f"星期：{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}"
        )

    def _format_date(self, kwargs) -> str:
        date_str = kwargs.get("date_str")
        format_str = kwargs.get("format_str", "%Y-%m-%d %H:%M:%S")
        
        if not date_str:
            return "错误：请提供日期字符串"
        
        try:
            # 尝试多种日期格式
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return f"格式化结果：{dt.strftime(format_str)}"
                except ValueError:
                    continue
            return f"错误：无法解析日期 '{date_str}'"
        except Exception as e:
            return f"日期格式化失败：{str(e)}"

    def _add_days(self, kwargs) -> str:
        date_str = kwargs.get("date_str")
        days = kwargs.get("days", 0)
        
        if not date_str:
            return "错误：请提供日期字符串"
        
        try:
            # 尝试解析日期
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
        except Exception as e:
            return f"日期计算失败：{str(e)}"

    def _date_diff(self, kwargs) -> str:
        date_str1 = kwargs.get("date_str")
        date_str2 = kwargs.get("format_str")  # 用 format_str 作为第二个日期
        
        if not date_str1 or not date_str2:
            return "错误：请提供两个日期字符串（date_str 和 format_str）"
        
        try:
            dt1 = None
            dt2 = None
            
            # 解析第一个日期
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
                try:
                    dt1 = datetime.strptime(date_str1, fmt)
                    break
                except ValueError:
                    continue
            
            # 解析第二个日期
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
                try:
                    dt2 = datetime.strptime(date_str2, fmt)
                    break
                except ValueError:
                    continue
            
            if dt1 is None or dt2 is None:
                return f"错误：无法解析日期"
            
            diff = abs((dt1 - dt2).days)
            
            return (
                f"日期1：{dt1.strftime('%Y-%m-%d')}\n"
                f"日期2：{dt2.strftime('%Y-%m-%d')}\n"
                f"相差天数：{diff} 天"
            )
        except Exception as e:
            return f"日期差计算失败：{str(e)}"
