import math
from typing import Any, Dict

from .base_tool import BaseTool


class CalculatorTool(BaseTool):
    """计算器工具，支持基本数学运算"""
    
    name = "calculator"
    description = "用于执行数学计算，支持加减乘除、幂运算、开方、三角函数等"
    parameters = {
        "expression": {
            "type": "string",
            "description": "要计算的数学表达式，例如: 2+3*4, sqrt(16), sin(3.14)"
        }
    }
    
    async def execute(self, **kwargs) -> str:
        expression = kwargs.get("expression", "")
        if not expression:
            return "错误：请提供要计算的表达式"
        
        try:
            # 安全的数学表达式计算
            allowed_funcs = {
                'abs': abs,
                'sqrt': math.sqrt,
                'pow': pow,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'pi': math.pi,
                'e': math.e,
            }
            result = eval(expression, {"__builtins__": {}}, allowed_funcs)
            return f"计算结果：{result}"
        except Exception as e:
            return f"计算错误：{str(e)}"
