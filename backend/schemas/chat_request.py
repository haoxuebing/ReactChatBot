from pydantic import BaseModel, Field

from .chat_message import ChatMessage


class ChatRequest(BaseModel):
    """聊天请求模型"""

    messages: list[ChatMessage] = Field(..., description="消息列表")
    stream: bool = Field(True, description="是否流式响应")
    session_id: str = Field("", description="会话ID，为空时自动生成")
    username: str = Field("", description="用户名，用于绑定会话归属")
