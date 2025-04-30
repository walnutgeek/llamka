import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from pydantic import BaseModel


class TypeInfo(NamedTuple):
    sql_type: str
    to_sql_fn: Callable[[Any], Any]
    from_sql_fn: Callable[[Any], Any]
    to_str_fn: Callable[[Any], str]

    @classmethod
    def get(cls, field_name: str) -> "TypeInfo":
        return _type_info_values[field_name]


class FieldInfo(NamedTuple):
    name: str
    type_info: TypeInfo
    description: str
    nullable: bool
    primary_key: bool
    foreign_key: tuple[str, str] | None

    @classmethod
    def build(cls, name: str, field_info: Any) -> "FieldInfo":
        type_name = (
            field_info.annotation.__name__
            if hasattr(field_info.annotation, "__name__")
            else str(field_info.annotation)
        )
        description = field_info.description
        is_nullable = type_name.endswith("| None")
        if is_nullable:
            type_name = type_name[:-6].strip()
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
            name=name,
            type_info=TypeInfo.get(type_name),
            description=description,
            nullable=is_nullable,
            primary_key=is_primary_key,
            foreign_key=foreign_key,
        )

    def to_sql_value(self, o: "DbModel") -> Any:
        v = getattr(o, self.name)
        return None if v is None else self.type_info.to_sql_fn(v)

    def from_sql_value(self, v: Any) -> Any:
        return None if v is None else self.type_info.from_sql_fn(v)

    def set_value(self, o: "DbModel", v: Any):
        setattr(o, self.name, self.from_sql_value(v))


class DbModel(BaseModel):
    @classmethod
    def get_field_infos(
        cls, filter: Callable[[FieldInfo], bool] = lambda _: True
    ) -> Generator[FieldInfo, None, None]:
        for field_name, field_info in cls.model_fields.items():
            fi = FieldInfo.build(field_name, field_info)
            if filter(fi):
                yield fi

    @classmethod
    def create_ddl(cls) -> str:
        fields = []
        for fi in cls.get_field_infos():
            type_name = (
                f"{fi.type_info.sql_type}{' NULL' if fi.nullable else ''}"
                + f"{' PRIMARY KEY' if fi.primary_key else ''}"
                + (
                    f" REFERENCES {fi.foreign_key[0]}({fi.foreign_key[1]})"
                    if fi.foreign_key
                    else ""
                )
            )
            fields.append(f"{fi.name} {type_name}")

        return f"CREATE TABLE {cls.__name__} (" + ", ".join(fields) + ")"

    def _insert(self, conn: sqlite3.Connection, auto_increment: bool = False):
        cursor = conn.cursor()
        cls = self.__class__
        fields = list(cls.get_field_infos(lambda fi: not auto_increment or not fi.primary_key))
        cursor.execute(
            f"INSERT INTO {cls.__name__} ({', '.join(map(lambda fi: fi.name, fields))}) "
            + f"VALUES ({', '.join(['?'] * len(fields))})",
            [fi.to_sql_value(self) for fi in fields],
        )
        if auto_increment:
            pks = list(cls.get_field_infos(lambda fi: fi.primary_key))
            assert len(pks) == 1
            pks[0].set_value(self, cursor.lastrowid)

    def save(self, conn: sqlite3.Connection):
        cls = self.__class__
        pks = list(cls.get_field_infos(lambda fi: fi.primary_key))
        if len(pks) == 1:
            pk = pks[0]
            pk_val = getattr(self, pk.name)
            if pk_val == -1:
                self._insert(conn, auto_increment=True)
                return
        n_updated = self._update(conn, pks)
        if n_updated == 0:
            self._insert(conn)
        else:
            assert n_updated == 1

    def _update(self, conn: sqlite3.Connection, pks: list[FieldInfo] | None = None) -> int:
        cursor = conn.cursor()
        cls = self.__class__
        if pks is None:
            pks = list(cls.get_field_infos(lambda fi: fi.primary_key))  # pragma: no cover
        non_pks = list(cls.get_field_infos(lambda fi: not fi.primary_key))
        cursor.execute(
            f"UPDATE {self.__class__.__name__} "
            + f"SET {', '.join([f'{fi.name} = ?' for fi in non_pks])} "
            + f"WHERE {', '.join([f'{fi.name} = ?' for fi in pks])}",
            [fi.to_sql_value(self) for fi in (non_pks + pks)],
        )
        return cursor.rowcount

    @classmethod
    def load_by_id(cls, conn: sqlite3.Connection, id: int) -> "DbModel | None":
        pks = list(cls.get_field_infos(lambda fi: fi.primary_key))
        fields = list(cls.get_field_infos())
        assert len(pks) == 1
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {', '.join([fi.name for fi in fields])} FROM {cls.__name__} "
            + f"WHERE {pks[0].name} = ?",
            [id],
        )
        row = cursor.fetchone()
        if row:
            return cls._from_row(row, fields)
        return None

    @classmethod
    def select(cls, conn: sqlite3.Connection, **filters: Any) -> list["DbModel"]:
        """Select all rows from the database that match the filters.

        Filters are given as keyword arguments, the keys are the field names
        and the values are the values to filter by.
        """
        fields = list(cls.get_field_infos())
        field_map = {fi.name: fi for fi in fields}
        unknown_filters = {k: filters[k] for k in filters if k not in field_map}
        assert len(unknown_filters) == 0, (
            f"Known fields: {field_map.keys()}, but unknown filters: {unknown_filters.keys()}"
        )
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {', '.join([fi.name for fi in fields])} FROM {cls.__name__} "
            + f"WHERE {' AND '.join([f'{k} = ?' for k in filters])}",
            [field_map[k].type_info.to_sql_fn(filters[k]) for k in filters],
        )
        return [cls._from_row(row, fields) for row in cursor.fetchall()]

    @classmethod
    def _from_row(cls, row: tuple[Any, ...], fields: list[FieldInfo] | None = None) -> "DbModel":
        if fields is None:
            fields = list(cls.get_field_infos())  # pragma: no cover
        return cls.model_validate(
            {fi.name: fi.from_sql_value(row[i]) for i, fi in enumerate(fields)}
        )


def to_sql_datetime(dt: datetime) -> str:
    return dt.isoformat()


_type_info_values = {
    "int": TypeInfo("INTEGER", int, int, str),
    "str": TypeInfo("TEXT", str, str, str),
    "Path": TypeInfo("TEXT", str, Path, str),
    "datetime": TypeInfo("TEXT", to_sql_datetime, datetime.fromisoformat, str),
}


@contextmanager
def open_sqlite_db(db_name: str | Path):
    """Open or create SQLite database with given name.

    Args:
        db_name: Path or name of the SQLite database file

    Yields:
        sqlite3.Connection: Database connection object
    """
    conn = sqlite3.connect(db_name)
    try:
        yield conn
    finally:
        conn.close()
