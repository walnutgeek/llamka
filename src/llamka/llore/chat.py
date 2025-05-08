import json
import logging
from datetime import datetime
from typing import Literal

import tornado.web
from pydantic import BaseModel, Field
from typing_extensions import override

from llamka.llore.pipeline import Llore
from llamka.llore.state.schema import ChatMessage
from llamka.service import AppService, AppState

logger = logging.getLogger("llore.chat")


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    session_id: int | None = None
    append_messages: list[ChatMessage]


class ChatCompletionResponse(BaseModel):
    session_id: int
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    messages: list[ChatMessage]


class Model(BaseModel):
    id: str
    description: str


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: list[Model]


class ChatAppState(AppState):
    """Application state for the chat service that maintains a Llore instance"""

    llore: Llore

    def __init__(self, port: int = 7532, debug: bool = False):
        super().__init__(ChatService(), port=port, debug=debug)
        self.llore = Llore()


class ChatService(AppService[ChatAppState]):
    """OpenAI-compatible chat API service"""

    def __init__(self):
        super().__init__()

        class ChatCompletionHandler(tornado.web.RequestHandler):
            @override
            def post(self):
                try:
                    body = json.loads(self.request.body)
                    session_id = -1
                    request = ChatCompletionRequest.model_validate(body)
                    if request.session_id is not None:
                        session_id = request.session_id
                    print(request)
                    # Create placeholder response
                    response = ChatCompletionResponse(
                        session_id=session_id,
                        messages=[
                            ChatMessage(role="assistant", content="This is a placeholder response"),
                        ],
                    )

                    self.write(response.model_dump_json())
                except Exception as e:
                    logger.error(f"Error in chat completion: {e}")
                    self.set_status(500)
                    self.write({"error": str(e)})

        class ModelsHandler(tornado.web.RequestHandler):
            @override
            def get(self):
                response = ModelList(
                    data=[Model(id="gpt-3.5-turbo", description="openai model older one")]
                )
                self.write(response.model_dump_json())

        self.add_route(r"/v1/chat/completions", ChatCompletionHandler)
        self.add_route(r"/v1/models", ModelsHandler)
