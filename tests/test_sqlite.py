from datetime import UTC, datetime
from pathlib import Path

import pytest

from llamka.llore.state import (
    FieldInfo,
    TypeInfo,
    open_sqlite_db,
)
from llamka.llore.state.schema import (
    Source,
    VectorizationAttempt,
    create_schema,
)


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
        VectorizationAttempt.create_ddl()
        == "CREATE TABLE VectorizationAttempt (attempt_id INTEGER PRIMARY KEY, source_id INTEGER REFERENCES Source(source_id), timestamp TEXT, n_chunks INTEGER, error TEXT NULL, sha256 TEXT)"
    )
    assert (
        Source.create_ddl()
        == "CREATE TABLE Source (source_id INTEGER PRIMARY KEY, absolute_path TEXT)"
    )


# test db cleanup
test_db_path = Path("build/tests/test.db")
if test_db_path.exists():
    test_db_path.unlink()
if not test_db_path.parent.is_dir():
    test_db_path.parent.mkdir(parents=True, exist_ok=True)


@pytest.mark.debug
def test_sqlite_db():
    create_schema(test_db_path)


@pytest.mark.debug
def test_add_attempt():
    with open_sqlite_db(test_db_path) as conn:
        s = Source(absolute_path=Path("test.txt"))
        assert s.source_id == -1
        s.save(conn)
        assert s.source_id != -1
        s_loaded = Source.load_by_id(conn, s.source_id)
        assert s_loaded == s
        assert isinstance(s_loaded.absolute_path , Path)
        a = VectorizationAttempt(
            source_id=s.source_id,
            timestamp=datetime.now(tz=UTC),
            n_chunks=1,
            error=None,
            sha256="1234567890",
        )
        assert a.attempt_id == -1
        a.save(conn)
        assert a.attempt_id != -1
        b = VectorizationAttempt(
            source_id=s.source_id,
            timestamp=datetime.now(tz=UTC),
            n_chunks=1,
            error=None,
            sha256="6789012345",
        )
        assert b.attempt_id == -1
        b.save(conn)
        assert b.attempt_id != -1
        assert b.attempt_id != a.attempt_id
        b.timestamp = datetime.now(tz=UTC)
        b.sha256 = "6172839405"
        b.save(conn)
        c = VectorizationAttempt(
            attempt_id=6,
            source_id=s.source_id,
            timestamp=datetime.now(tz=UTC),
            n_chunks=6,
            error=None,
            sha256="1122334455",
        )
        c.save(conn)
        a_loaded = VectorizationAttempt.load_by_id(conn, a.attempt_id)
        b_loaded = VectorizationAttempt.load_by_id(conn, b.attempt_id)
        c_loaded = VectorizationAttempt.load_by_id(conn, c.attempt_id)
        nothing_loaded = VectorizationAttempt.load_by_id(conn, 7)
        assert nothing_loaded is None
        assert a_loaded == a, f"{a_loaded=} != {a=}"
        assert b_loaded == b, f"{b_loaded=} != {b=}"
        assert c_loaded == c, f"{c_loaded=} != {c=}"
        assert isinstance(a_loaded.timestamp, datetime)
        assert isinstance(b_loaded.timestamp, datetime)
        assert isinstance(c_loaded.timestamp, datetime)
        select = VectorizationAttempt.select(conn, source_id=s.source_id)
        assert len(select) == 3
        assert a in select
        assert b in select
        assert c in select
        conn.commit()
