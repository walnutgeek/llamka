import base64
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from tornado.httpclient import HTTPRequest

from llamka.llore.utils import get_adjust_to_root_modifier, modify_path_attributes
from llamka.service import get_json

log = logging.getLogger(__name__)


class ChatModel(BaseModel):
    name: str
    url: str
    api_key: str
    params: dict[str, Any]


class BasicAuth(BaseModel):
    username: str
    password: str

    def encode(self) -> str:
        return base64.b64encode(f"{self.username}:{self.password}".encode()).decode()

DIALECTS={
    "copilot": {
        "model":"modelId", 
        "messages": "chatCompletionMessages", 
        "role": "promptRole", 
        "content": "promptRole",
    }}

def transate(dialect: Literal["auto", "copilot"], json: Any) -> Any:
    if dialect == "auto":
        return json
    assert dialect in DIALECTS, f"Unknown dialect: {dialect}"
    dictionary = DIALECTS[dialect]
    if isinstance(json, list):
        return [transate(dialect, v) for v in json]
    elif isinstance(json, dict):
        new_json = {}
        for k, v in json.items():
            new_k = dictionary.get(k, k)
            if isinstance(v, dict):
                v = transate(dialect, v)
            elif isinstance(v, list):
                v = [transate(dialect, v) for v in v]
            new_json[new_k] = v
        return new_json
    else:
        return json

class LLMModelConfig(BaseModel):
    model_name: str
    dialect: Literal["auto", "copilot"] = Field(default="auto")
    context_window: int|None = Field(default=None)
    url: str
    stream: bool = Field(default=False)
    api_key: str | None = Field(default=None)
    basic_auth: BasicAuth | None = Field(default=None)
    params: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)

    

    async def query(
        self,
        messages: list[dict[str, Any]],
        to_json: Callable[[Any], Any] = json.loads,
        request_timeout: float = 100,
    ) -> Any:
        
        req_body: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
        }
        if self.dialect != "auto":
            req_body = transate(self.dialect, req_body)
        if self.params:
            req_body.update(self.params)
        req_body["stream"] = self.stream
        log.debug(f"Request body: {req_body}")
        headers = {}
        if self.headers:
            for k, v in self.headers.items():
                if v is None:
                    n = k.lower().replace("-", "_")
                    if "timestamp" in n:
                        v = str(datetime.now().replace(microsecond=0).astimezone().isoformat())
                    elif "request_id" in n:
                        v = str(uuid.uuid1())
                    else:
                        continue
                headers[k] = v
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        log.debug(f"Request before Authorization headers: {headers}")
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.basic_auth:
            headers["Authorization"] = f"Basic {self.basic_auth.encode()}"
        req = HTTPRequest(
            url=self.url,
            method="POST",
            body=json.dumps(req_body),
            headers=headers,
            request_timeout=request_timeout,
        )
        return await get_json(req, to_json=to_json)


class EmbeddingModel(BaseModel):
    model_name: str
    model_params: dict[str, Any]
    encode_params: dict[str, Any]
    cache_model: bool = Field(default=True)
    cache_path: Path | None = Field(default=None)


class VectorDb(BaseModel):
    dir: Path
    embeddings: EmbeddingModel


class FileGlob(BaseModel):
    dir: Path
    glob: str

    def get_matching_files(self) -> list[Path]:
        return list(self.dir.glob(self.glob))


class Config(BaseModel):
    bots: FileGlob
    state_path: Path
    hf_hub_dir: Path
    vector_db: VectorDb
    llm_models: dict[str, LLMModelConfig]


class ModelParams(BaseModel):
    name: str
    params: dict[str, Any]


class RagConfig(BaseModel):
    files: list[FileGlob]
    vector_db_collection: str


class BotConfig(BaseModel):
    name: str
    model: ModelParams
    rag: RagConfig | None = Field(default=None)


def load_config(
    path: str | Path, root: str | Path | None = None
) -> tuple[Path | None, Config, list[BotConfig]]:
    root = Path(root).absolute() if root is not None else None
    path_modifier = get_adjust_to_root_modifier(root)
    path = path_modifier(Path(path))
    config = Config.model_validate_json(path.read_text())
    modify_path_attributes(config, path_modifier)
    bots: list[BotConfig] = []
    for f in config.bots.get_matching_files():
        bot = BotConfig.model_validate_json(f.read_text())
        modify_path_attributes(bot, path_modifier)
        bots.append(bot)
    return root, config, bots
