import hashlib
import traceback
from datetime import UTC, datetime
from pathlib import Path

from llamka.llore.config import BotConfig, Config, load_config
from llamka.llore.state import open_sqlite_db
from llamka.llore.state.schema import (
    ActionType,
    RagAction,
    RagActionCollection,
    RagSource,
    check_all_tables_exist,
    create_tables,
    select_all_active_sources,
)
from llamka.llore.vector import (
    get_vector_collection,
    load_document_into_chunks,
)


class FileTransition:
    present_before_sha256: str | None
    present_after: bool

    def __init__(self, present_before_sha256: str | None, present_after: bool):
        self.present_before_sha256 = present_before_sha256
        self.present_after = present_after

    def future_action(self, state: "FileState") -> ActionType | None:
        if self.present_before_sha256 is None:
            if self.present_after:
                return "new"
        elif self.present_after:
            assert bool(state.sha256()), f"{state.path} is missing"
            if self.present_before_sha256 != state.sha256():
                return "update"
        else:
            return "delete"
        return None


class FileState:
    path: Path
    collections: dict[str, FileTransition]
    _sha256: str | None

    def __init__(self, path: Path):
        self.path = path
        self.collections = {}
        self._sha256 = None

    def sha256(self) -> str:
        if self._sha256 is None:
            if self.path.exists():
                self._sha256 = hashlib.sha256(self.path.read_bytes()).hexdigest()
            else:
                self._sha256 = ""
        return self._sha256


class FileStates:
    states: dict[Path, FileState]

    def __init__(self):
        self.states = {}

    def add_file(self, path: Path) -> FileState:
        path = path.absolute()
        if path not in self.states:
            self.states[path] = FileState(path)
        return self.states[path]


class Llore:
    config: Config
    bots: list[BotConfig]

    def __init__(self):
        self.config, self.bots = load_config("data/config.json")

    def process_files(self):
        file_states = FileStates()
        for bot in self.bots:
            for glob in bot.files:
                for file in glob.get_matching_files():
                    fstate = file_states.add_file(file)
                    fstate.collections[bot.vector_db_collection] = FileTransition(None, True)

        with open_sqlite_db(self.config.state_path / "state.db") as conn:
            if not check_all_tables_exist(conn):
                create_tables(conn)
            sources, actions, collections = zip(*select_all_active_sources(conn), strict=False)
            for i in range(len(sources)):
                source = sources[i]
                file_state = file_states.add_file(source.absolute_path)
                for c in collections:
                    if c.action == "delete":
                        continue
                    if c.collection not in file_state.collections:
                        file_state.collections[c.collection] = FileTransition(None, False)
                    file_state.collections[c.collection].present_before_sha256 = actions[i].sha256

        for state in file_states.states.values():
            deletes: list[str] = []
            pending_uploads: list[tuple[str, ActionType]] = []
            for collection, transition in state.collections.items():
                action = transition.future_action(state)
                if action is not None:
                    if action == "delete":
                        deletes.append(collection)
                    else:
                        pending_uploads.append((collection, action))
            if not deletes and not pending_uploads:
                continue
            source = self.store_source(state.path)
            action = None
            if pending_uploads:
                try:
                    chunks = load_document_into_chunks(state.path)
                    if len(chunks) == 0:
                        print(f"No chunks for {state.path}")
                        continue
                    action = self.store_action(source, len(chunks), state)
                    for collection, action_type in pending_uploads:
                        db = get_vector_collection(self.config, collection)
                        if action_type == "update":
                            db.delete(where={"metadata": {"source": str(state.path)}})
                        db.add_documents(chunks)

                        self.store_collection_action(action, collection, action_type)
                except Exception as e:
                    print(f"Error loading document {state.path}: {e}")
                    error = traceback.format_exc()
                    print(error)
                    continue
            if deletes:
                if action is None:
                    action = self.store_action(source, 0, state)
                for collection in deletes:
                    db = get_vector_collection(self.config, collection)
                    db.delete(where={"metadata": {"source": str(state.path)}})
                    self.store_collection_action(action, collection, "delete")

    def store_source(self, path: Path) -> RagSource:
        with open_sqlite_db(self.config.state_path / "state.db") as conn:
            sources = RagSource.select(conn, absolute_path=path)
            if len(sources) == 0:
                source = RagSource(absolute_path=path)
                source.save(conn)
                return source
            else:
                assert len(sources) == 1, f"Multiple sources for {path}"
                return sources[0]

    def store_action(self, source: RagSource, n_chunks: int, state: FileState) -> RagAction:
        with open_sqlite_db(self.config.state_path / "state.db") as conn:
            action = RagAction(
                source_id=source.source_id,
                timestamp=datetime.now(tz=UTC),
                n_chunks=n_chunks,
                error=None,
                sha256=state.sha256(),
            )
            action.save(conn)
            return action

    def store_collection_action(
        self, action: RagAction, collection: str, action_type: ActionType
    ) -> RagActionCollection:
        with open_sqlite_db(self.config.state_path / "state.db") as conn:
            collection_action = RagActionCollection(
                action_id=action.action_id,
                action=action_type,
                collection=collection,
                timestamp=datetime.now(tz=UTC),
            )
            collection_action.insert(conn)
            return collection_action

    def run(self):
        pass
