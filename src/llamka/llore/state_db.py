from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from pydantic import BaseModel, Field


class Source(BaseModel):
    source_id: int = Field(description="(PK) Unique identifier for the source")
    absolute_path: Path = Field(description="Absolute path to the source file")


class VectorizationAttempt(BaseModel):
    attempt_id: int = Field(description="(PK) Unique identifier for the attempt")
    source_id: int = Field(
        description="(FK:Source.source_id) Reference to the source being vectorized"
    )
    timestamp: datetime = Field(description="When the attempt was made")
    n_chunks: int = Field(description="Number of chunks created", ge=0)
    error: str | None = Field(default=None, description="Error message if vectorization failed")
    sha256: str = Field(description="SHA256 hash of the original file")


class KnownSources(BaseModel):
    files: list[Source] = Field(description="List of known source files")


class TypeInfo(NamedTuple):
    sql_type: str
    to_val_fn: type
    to_str_fn: Callable[[Any], str] = str

    @classmethod
    def get(cls, field_name: str) -> "TypeInfo":
        return _type_info_values[field_name]


class FieldInfo(NamedTuple):
    type_info: TypeInfo
    description: str
    nullable: bool
    primary_key: bool
    foreign_key: tuple[str, str] | None

    @classmethod
    def from_field_info(cls, field_info: Any) -> "FieldInfo":
        n = (
            field_info.annotation.__name__
            if hasattr(field_info.annotation, "__name__")
            else str(field_info.annotation)
        )
        description = field_info.description
        is_nullable = n.endswith("| None")
        if is_nullable:
            n = n[:-6].strip()
        is_primary_key = description.startswith("(PK)")
        if is_primary_key:
            description = description[4:].strip()
        assert not (is_primary_key and is_nullable), (
            "A field cannot be both a primary key and nullable"
        )

        is_foreign_key = description.startswith("(FK:")
        if is_foreign_key:
            x, description = description[4:].strip().split(")")
            table_name, field_name = x.split(".")
            foreign_key = table_name, field_name
        else:
            foreign_key = None
        return cls(
            type_info=_type_info_values[n],
            description=description,
            nullable=is_nullable,
            primary_key=is_primary_key,
            foreign_key=foreign_key,
        )


_type_info_values = {
    "int": TypeInfo("INTEGER", int, str),
    "str": TypeInfo("TEXT", str, str),
    "Path": TypeInfo("TEXT", Path, str),
    "datetime": TypeInfo("TEXT", datetime, str),
}


def create_ddl_from_model(model_cls: type[BaseModel]) -> str:
    """Create a DDL from a Pydantic model"""
    fields = []
    for field_name, field_info in model_cls.model_fields.items():
        # Get the Python type name from the annotation
        fi = FieldInfo.from_field_info(field_info)
        type_name = (
            f"{fi.type_info.sql_type}{' NULL' if fi.nullable else ''}"
            + f"{' PRIMARY KEY' if fi.primary_key else ''}"
            + (f" REFERENCES {fi.foreign_key[0]}({fi.foreign_key[1]})" if fi.foreign_key else "")
        )
        fields.append(f"{field_name} {type_name}")

    return f"CREATE TABLE {model_cls.__name__} (" + ", ".join(fields) + ")"
