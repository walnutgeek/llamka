import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from pydantic import Field

from llamka.llore.state import DbModel, from_multi_model_row, open_sqlite_db

ActionType = Literal["new", "update", "delete"]


class RagSource(DbModel["RagSource"]):
    source_id: int = Field(default=-1, description="(PK) Unique identifier for the source")
    absolute_path: Path = Field(description="Absolute path to the source file")


class RagAction(DbModel["RagAction"]):
    action_id: int = Field(default=-1, description="(PK) Unique identifier for the attempt")
    source_id: int = Field(
        description="(FK:RagSource.source_id) Reference to the source being vectorized"
    )
    timestamp: datetime = Field(description="When the attempt was made")
    n_chunks: int = Field(description="Number of chunks created", ge=0)
    error: str | None = Field(default=None, description="Error message if vectorization failed")
    sha256: str = Field(description="SHA256 hash of the original file")


class RagActionCollection(DbModel["RagActionCollection"]):
    action_id: int = Field(
        description="(FK:RagAction.action_id) Reference to the action being vectorized"
    )
    action: ActionType = Field(description="Action taken on the source")
    collection: str = Field(description="Name of the collection the action was applied to")
    timestamp: datetime = Field(description="When the attempt was made")


tables = [RagSource, RagAction, RagActionCollection]


def check_all_tables_exist(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ")
    all_tables = set(r[0] for r in cursor.fetchall())
    return all(t.get_table_name() in all_tables for t in tables)


def create_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()
    for table in tables:
        cursor.execute(table.create_ddl())
    conn.commit()


def create_schema(path: Path):
    with open_sqlite_db(path) as conn:
        create_tables(conn)


def select_all_active_sources(
    conn: sqlite3.Connection,
) -> list[tuple[RagSource, RagAction, list[RagActionCollection]]]:
    cursor = conn.cursor()
    cursor.execute(
        f"WITH timestamps as (SELECT a.source_id, max(a.timestamp) as last_action_timestamp FROM {RagAction.alias('a')} GROUP BY a.source_id), "
        + f" last_actions as ( SELECT a.action_id FROM {RagAction.alias('a')}, timestamps t WHERE a.source_id = t.source_id AND a.timestamp = t.last_action_timestamp)"
        + f" SELECT {RagSource.columns('s')}, {RagAction.columns('a')}, {RagActionCollection.columns('c')} "
        + f"   FROM {RagSource.alias('s')}, {RagAction.alias('a')}, {RagActionCollection.alias('c')}, last_actions l "
        + "   WHERE s.source_id = a.source_id AND l.action_id = a.action_id AND c.action_id = a.action_id ORDER BY a.source_id"
    )
    sources = [
        cast(
            tuple[RagSource, RagAction, RagActionCollection],
            tuple(from_multi_model_row(row, [RagSource, RagAction, RagActionCollection])),
        )
        for row in cursor.fetchall()
    ]
    agg: list[tuple[RagSource, RagAction, list[RagActionCollection]]] = []
    if len(sources) > 0:
        start = 0
        i = 0
        while True:
            prev_a = sources[i][1]
            while True:
                i += 1
                if i >= len(sources) or sources[i][1].action_id != prev_a.action_id:
                    break
            collections = [c for _, _, c in sources[start:i]]
            agg.append((sources[start][0], prev_a, collections))
            if i >= len(sources):
                break
            start = i
    return agg
