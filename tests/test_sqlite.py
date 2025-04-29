import pytest

from llamka.llore.state_db import (
    FieldInfo,
    Source,
    TypeInfo,
    VectorizationAttempt,
    create_ddl_from_model,
)


@pytest.mark.debug
def test_type_info():
    assert FieldInfo.from_field_info(VectorizationAttempt.model_fields["timestamp"]) == (
        TypeInfo.get("datetime"),
        "When the attempt was made",
        False,
        False,
        None,
    )


@pytest.mark.debug
def test_dll():
    assert (
        create_ddl_from_model(VectorizationAttempt)
        == "CREATE TABLE VectorizationAttempt (attempt_id INTEGER PRIMARY KEY, source_id INTEGER REFERENCES Source(source_id), timestamp TEXT, n_chunks INTEGER, error TEXT NULL, sha256 TEXT)"
    )
    assert (
        create_ddl_from_model(Source)
        == "CREATE TABLE Source (source_id INTEGER PRIMARY KEY, absolute_path TEXT)"
    )
