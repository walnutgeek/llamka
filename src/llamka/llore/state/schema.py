from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from llamka.llore.state import DbModel, open_sqlite_db


class Source(DbModel["Source"]):
    source_id: int = Field(default=-1, description="(PK) Unique identifier for the source")
    absolute_path: Path = Field(description="Absolute path to the source file")


class VectorizationAttempt(DbModel["VectorizationAttempt"]):
    attempt_id: int = Field(default=-1, description="(PK) Unique identifier for the attempt")
    source_id: int = Field(
        description="(FK:Source.source_id) Reference to the source being vectorized"
    )
    timestamp: datetime = Field(description="When the attempt was made")
    n_chunks: int = Field(description="Number of chunks created", ge=0)
    error: str | None = Field(default=None, description="Error message if vectorization failed")
    sha256: str = Field(description="SHA256 hash of the original file")


class KnownSources(BaseModel):
    files: list[Source] = Field(description="List of known source files")


def create_schema(path: Path):
    with open_sqlite_db(path) as conn:
        cursor = conn.cursor()
        cursor.execute(Source.create_ddl())
        cursor.execute(VectorizationAttempt.create_ddl())
        conn.commit()
