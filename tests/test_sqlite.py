from datetime import UTC, datetime
from pathlib import Path

import pytest

from llamka.llore.state import (
    FieldInfo,
    TypeInfo,
    create_ddl_from_model,
    open_sqlite_db,
)
from llamka.llore.state.schema import (
    Source,
    VectorizationAttempt,
    create_schema,
)

test_db_path = Path("build/tests/test.db")
if test_db_path.exists():
    test_db_path.unlink()
if not test_db_path.parent.is_dir():
    test_db_path.parent.mkdir(parents=True, exist_ok=True)


@pytest.mark.debug
def test_type_info():
    assert FieldInfo.build("timestamp", VectorizationAttempt.model_fields["timestamp"]) == (
        "timestamp",
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


@pytest.mark.debug
def test_sqlite_db():
    create_schema(test_db_path)


@pytest.mark.debug
def test_add_attempt():
    with open_sqlite_db(test_db_path) as conn:
        src = Source(absolute_path=Path("test.txt"))
        src.save(conn)
        a = VectorizationAttempt(
            source_id=src.source_id,
            timestamp=datetime.now(tz=UTC),
            n_chunks=1,
            error=None,
            sha256="1234567890",
        )
        a.save(conn)
        assert a.attempt_id != -1
        loaded = VectorizationAttempt.load_by_id(conn, a.attempt_id)
        assert loaded == a, f"{loaded=} != {a=}"
        conn.commit()
