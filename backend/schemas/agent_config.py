from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """智能体配置"""
    enable_tools: bool = Field(True, description="是否启用工具调用")
    memory_limit: int = Field(100, description="记忆消息上限")
    temperature: float = Field(0.7, description="模型温度参数")
