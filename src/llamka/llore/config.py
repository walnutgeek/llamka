from pathlib import Path
from typing import Any

from pydantic import BaseModel


class ChatModel(BaseModel):
    name: str
    url: str
    api_key: str
    params: dict[str, Any]


class EmbeddingModel(BaseModel):
    model_name: str
    model_params: dict[str, Any]
    encode_params: dict[str, Any]


class VectorDb(BaseModel):
    # type: str
    vector_db_path: Path
    collection_name: str

    def ensure_dir(self):
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        return str(self.vector_db_path)


class Vectorization(BaseModel):
    vector_db: VectorDb
    embedding: EmbeddingModel


class StateDb(BaseModel):
    state_db_path: Path
    type: str
    params: dict[str, Any]


class Config(BaseModel):
    files: list[str]
    models: list[ChatModel]
    vectorization: Vectorization

    def get_paths(self) -> list[Path]:
        return [Path(f).expanduser().absolute() for f in self.files]


def load_config(path: str) -> Config:
    with open(path) as f:
        return Config.model_validate_json(f.read())
