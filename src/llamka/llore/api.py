from typing import Any

from pydantic import BaseModel, Field, model_validator


class Models(BaseModel):
    llms: list[str]
    bots: list[str]


class TooledMessages(BaseModel):
    tooled_messages: list["ChatMsg"]
    # tooled_at: datetime
    tooled_by: str


class ChatMsg(BaseModel):
    role: str
    content: str
    # created: datetime | None = Field(default=None)
    tooled: TooledMessages | None = Field(default=None)

    def to_output_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content}


class ChatRequest(BaseModel):
    bot_name: str | None = Field(default=None)
    llm_name: str | None = Field(default=None)
    messages: list[ChatMsg]

    @model_validator(mode="before")
    @classmethod
    def validate_before_creation(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values.get("bot_name", None) is None and values.get("llm_name", None) is None:
            raise ValueError("Either bot_name or llm_name must be provided")
        return values


class ChatResponse(BaseModel):
    generation: ChatMsg
