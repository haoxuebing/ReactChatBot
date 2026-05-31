from pydantic import BaseModel, Field


class UsernameRequest(BaseModel):
    """用户名注册/绑定请求"""
    username: str = Field(..., min_length=1, max_length=12, description="用户名")


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    username: str = Field(..., min_length=1, max_length=12, description="用户名")
    session_id: str = Field("", description="会话ID，为空时自动生成")
