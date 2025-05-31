from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import BaseMessage, ChatMessage
from langchain_core.outputs import ChatResult
from langchain_core.outputs.chat_generation import ChatGeneration


def base_message_to_dict(message: BaseMessage) -> dict[str, Any]:
    return {"role": message.type, "content": message.content}


def response_to_chat_result(response: dict[str, Any]) -> ChatResult:
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
    else:
        raise ValueError(f"Unsupported response format: {response}")

    return ChatResult(
        generations=[
            ChatGeneration(
                message=ChatMessage(
                    content=content, role=role, additional_kwargs={"created": created.isoformat()}
                )
            )
        ]
    )
