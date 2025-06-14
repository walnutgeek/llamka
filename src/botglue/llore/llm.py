import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel

from botglue.llore.api import ChatMsg, ChatResponse, TooledMessages

logger = logging.getLogger(__name__)


def flatten_tooled_messages(
    msgs: list[ChatMsg], expand_tooled: Callable[[ChatMsg], bool] = lambda _: True
) -> list[ChatMsg]:
    def _flatten(msg: ChatMsg) -> Generator[ChatMsg, None, None]:
        if msg.tooled is not None and expand_tooled(msg):
            yield from msg.tooled.tooled_messages
        else:
            yield msg

    return [m for p in msgs for m in _flatten(p)]


def extract_tool_name(msg: ChatMsg | str) -> str | None:
    role = msg if isinstance(msg, str) else msg.role
    if role.startswith("tool:"):
        return role[5:]
    return None


def response_to_chat_result(response: dict[str, Any]) -> ChatResponse:
    # Handle OpenAI format
    if "choices" in response:
        choices = response["choices"]
        assert len(choices) == 1
        ch = choices[0]
        content = ch["message"]["content"]
        role = ch["message"]["role"]
        created = datetime.fromtimestamp(response["created"])
    # Handle Ollama format
    elif "message" in response:
        content = response["message"]["content"]
        role = response["message"]["role"]
        created = datetime.fromisoformat(response["created_at"].replace("Z", "+00:00"))
    # Handle Claude format
    elif "content" in response:
        content = response["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        content = content[0]["text"]
        role = response["role"]
        created = datetime.now(UTC)
    elif "chatCompletion" in response:
        content = response["chatCompletion"]["chatCompletionContent"]
        role = "assistant"
        created = datetime.now(UTC)
    else:
        raise ValueError(f"Unsupported response format: {response}")

    logger.debug(f"Response: {created}")
    return ChatResponse(generation=ChatMsg(content=content, role=role))


class Tool(metaclass=ABCMeta):
    config_type: ClassVar[type[BaseModel]]
    name: str

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def __call__(self, input: ChatMsg) -> list[ChatMsg]:
        raise NotImplementedError


class ToolMap:
    tools: dict[str, Tool]

    def __init__(self):
        self.tools = {}

    def update(self, tool: Tool):
        self.tools[tool.name] = tool

    def has_tool(self, input: ChatMsg) -> bool | None:
        tool_name = extract_tool_name(input)
        return None if tool_name is None else tool_name in self.tools

    def __call__(self, input: ChatMsg) -> bool:
        tool_name = extract_tool_name(input)
        if tool_name:
            try:
                tooled_msgs = self.tools[tool_name](input)
                input.tooled = TooledMessages(tooled_messages=tooled_msgs, tooled_by=tool_name)
                # TODO: tooled_at tooled_at=datetime.now(UTC),
                return True
            except KeyError:
                logger.warning(f"No such tool: {tool_name}")
        return False
