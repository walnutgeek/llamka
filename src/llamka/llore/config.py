import base64
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from tornado.httpclient import HTTPRequest

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


class LLMModelConfig(BaseModel):
    model_name: str
    context_window: int
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
    ) -> Any:
        req_body: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
        }
        if self.params:
            req_body.update(self.params)
        req_body["stream"] = self.stream
        log.warning(f"Request body: {req_body}")
        headers = {}
        if self.headers:
            headers.update(self.headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.basic_auth:
            headers["Authorization"] = f"Basic {self.basic_auth.encode()}"
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        req = HTTPRequest(url=self.url, method="POST", body=json.dumps(req_body), headers=headers)
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

    def get_matching_files(self, root: Path | None = None) -> list[Path]:
        dir = root / self.dir if root is not None else self.dir
        return list(dir.glob(self.glob))


class Config(BaseModel):
    bots: FileGlob
    state_path: Path
    hf_hub_dir: Path
    vector_db: VectorDb
    llm_models: dict[str, LLMModelConfig]


class ModelParams(BaseModel):
    name: str
    params: dict[str, Any]


class BotConfig(BaseModel):
    name: str
    files: list[FileGlob]
    vector_db_collection: str
    model: ModelParams


def load_config(
    path: str | Path, root: str | Path | None = None
) -> tuple[Path | None, Config, list[BotConfig]]:
    if root is None:
        path = Path(path)
    else:
        root = Path(root).absolute()
        path = root / path
    config = Config.model_validate_json(path.read_text())
    bots = [
        BotConfig.model_validate_json(f.read_text()) for f in config.bots.get_matching_files(root)
    ]
    return root, config, bots
