from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """工具基类，定义工具的基本接口"""
    
    name: str
    description: str
    parameters: Dict[str, Any]
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具并返回结果"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """将工具转换为模型可理解的格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }
