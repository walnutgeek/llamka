from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ChatModel(BaseModel):
    name: str
    url: str
    api_key: str
    params: dict[str, Any]


class BasicAuth(BaseModel):
    username: str
    password: str


class LLMModel(BaseModel):
    model_name: str
    context_window: int
    stream: bool
    url: str
    api_key: str | None = Field(default=None)
    basic_auth: BasicAuth | None = Field(default=None)
    params: dict[str, Any] = Field(default_factory=dict)


class EmbeddingModel(BaseModel):
    model_name: str
    model_params: dict[str, Any]
    encode_params: dict[str, Any]


class VectorDb(BaseModel):
    dir: Path
    embeddings: EmbeddingModel

    def ensure_dir(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        return str(self.dir)


class FileGlob(BaseModel):
    dir: Path
    glob: str

    def get_matching_files(self) -> list[Path]:
        return list(self.dir.glob(self.glob))


class Config(BaseModel):
    bots: FileGlob
    state_path: Path
    vector_db: VectorDb
    llm_models: dict[str, LLMModel]


class ModelParams(BaseModel):
    name: str
    params: dict[str, Any]


class BotConfig(BaseModel):
    name: str
    files: list[FileGlob]
    vector_db_collection: str
    model: ModelParams


def load_config(path: str) -> tuple[Config, list[BotConfig]]:
    config = Config.model_validate_json(open(path).read())
    bots = [
        BotConfig.model_validate_json(open(f).read())
        for f in config.bots.dir.glob(config.bots.glob)
    ]
    return config, bots
