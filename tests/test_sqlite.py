from datetime import UTC, datetime
from pathlib import Path
import time

import pytest

from llamka.llore.state import (
    FieldInfo,
    TypeInfo,
    open_sqlite_db,
)
from llamka.llore.state.schema import (
    RagAction,
    RagActionCollection,
    RagSource,
    create_schema,
    select_all_active_sources,
)


@pytest.mark.debug
def test_type_info():
    assert FieldInfo.build("timestamp", RagAction.model_fields["timestamp"]) == (
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
        RagAction.create_ddl()
        == "CREATE TABLE RagAction (action_id INTEGER PRIMARY KEY, source_id INTEGER REFERENCES RagSource(source_id), timestamp TEXT, n_chunks INTEGER, error TEXT NULL, sha256 TEXT)"
    )
    assert (
        RagSource.create_ddl()
        == "CREATE TABLE RagSource (source_id INTEGER PRIMARY KEY, absolute_path TEXT)"
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
        select = select_all_active_sources(conn)
        assert len(select) == 0
        s = RagSource(absolute_path=Path("test.txt"))
        assert s.source_id == -1
        s.save(conn)
        assert s.source_id != -1
        s_loaded = RagSource.load_by_id(conn, s.source_id)
        assert s_loaded is not None
        assert s_loaded == s
        assert isinstance(s_loaded.absolute_path, Path)
        a1 = RagAction(
            source_id=s.source_id,
            timestamp=datetime.now(tz=UTC),
            n_chunks=1,
            error=None,
            sha256="1234567890",
        )
        assert a1.action_id == -1
        a1.save(conn)
        time.sleep(.001)
        assert a1.action_id != -1
        c1 = RagActionCollection(
            action_id=a1.action_id,
            action="new",
            collection="test",
            timestamp=datetime.now(tz=UTC),
        )
        c1.insert(conn)
        time.sleep(.001)
        a2 = RagAction(
            source_id=s.source_id,
            timestamp=datetime.now(tz=UTC),
            n_chunks=1,
            error=None,
            sha256="6789012345",
        )
        assert a2.action_id == -1
        a2.save(conn)
        time.sleep(.001)
        assert a2.action_id != -1
        assert a2.action_id != a1.action_id
        c2 = RagActionCollection(
            action_id=a2.action_id,
            action="new",
            collection="test",
            timestamp=datetime.now(tz=UTC),
        )
        c2.insert(conn)
        time.sleep(.001) 
        a2.timestamp = datetime.now(tz=UTC)
        a2.sha256 = "6172839405"
        a2.save(conn)
        time.sleep(.001)
        select = select_all_active_sources(conn)
        if len(select) != 1:
            print(f"{select=}")
            raise AssertionError(f"{select=}")
        
        assert len(select[0][2]) == 1

        a3 = RagAction(
            action_id=6,
            source_id=s.source_id,
            timestamp=datetime.now(tz=UTC),
            n_chunks=6,
            error=None,
            sha256="1122334455",
        )
        a3.save(conn)
        time.sleep(.001)
        c3 = RagActionCollection(
            action_id=a3.action_id,
            action="update",
            collection="test",
            timestamp=datetime.now(tz=UTC),
        )
        c3.insert(conn)
        time.sleep(.001)
        c4 = RagActionCollection(
            action_id=a3.action_id,
            action="new",
            collection="test2",
            timestamp=datetime.now(tz=UTC),
        )
        c4.insert(conn)
        time.sleep(.001)
        a1_loaded = RagAction.load_by_id(conn, a1.action_id)
        a2_loaded = RagAction.load_by_id(conn, a2.action_id)
        a3_loaded = RagAction.load_by_id(conn, a3.action_id)
        nothing_loaded = RagAction.load_by_id(conn, 7)
        assert nothing_loaded is None
        assert a1_loaded is not None
        assert a2_loaded is not None
        assert a3_loaded is not None
        assert a1_loaded == a1, f"{a1_loaded=} != {a1=}"
        assert a2_loaded == a2, f"{a2_loaded=} != {a2=}"
        assert a3_loaded == a3, f"{a3_loaded=} != {a3=}"
        assert isinstance(a1_loaded.timestamp, datetime)
        assert isinstance(a2_loaded.timestamp, datetime)
        assert isinstance(a3_loaded.timestamp, datetime)
        select = RagAction.select(conn, source_id=s.source_id)
        assert len(select) == 3
        assert a1 in select
        assert a2 in select
        assert a3 in select
        select = select_all_active_sources(conn)
        assert len(select) == 1
        s_loaded2, a_loaded2, c_loaded2 = select[0]
        assert s_loaded2 == s
        assert a_loaded2 == a3
        assert isinstance(c_loaded2, list)
        assert len(c_loaded2) == 2
        conn.commit()
