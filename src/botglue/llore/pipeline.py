import hashlib
import logging
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from langchain_core.prompt_values import ChatPromptValue
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from botglue.llore.api import ChatMsg, ChatResponse, Models
from botglue.llore.config import BotConfig, Config, load_config
from botglue.llore.llm import response_to_chat_result
from botglue.llore.state import open_sqlite_db
from botglue.llore.state.schema import (
    ActionType,
    RagAction,
    RagActionCollection,
    RagSource,
    check_all_tables_exist,
    create_tables,
    select_all_active_sources,
)
from botglue.llore.vector import (
    get_vector_collection,
    load_document_into_chunks,
)
from botglue.misc import ensure_dir

logger = logging.getLogger("llore.pipeline")


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


# TODO: langchain pipeline


class Llore:
    root: Path | None
    config: Config
    bots: dict[str, BotConfig]

    def __init__(
        self, config_path: str | Path = "data/config.json", root: str | Path | None = None
    ):
        self.root, self.config, bots = load_config(config_path, root)
        self.bots = {b.name: b for b in bots}

    async def query_llm(self, llm_name: str, messages: list[ChatMsg]) -> ChatResponse:
        llm = self.config.llm_models[llm_name]
        return response_to_chat_result(await llm.query([m.to_output_dict() for m in messages]))

    async def query_bot(
        self, bot_name: str, messages: list[ChatMsg], llm_name: str | None = None
    ) -> ChatResponse:
        bot_cfg = self.bots[bot_name]
        if bot_cfg.rag is not None and len(messages) > 0 and messages[-1].role == "user":
            question = messages[-1].content

            db = get_vector_collection(self.config, bot_cfg.rag.vector_db_collection)

            retriever = db.as_retriever()
            template = """Answer the question based only on the following context:
{context}

Please provide document name and page numbers as reference.

Question: {question}
"""
            prompt = ChatPromptTemplate.from_template(template)

            retrieval_chain = {"context": retriever, "question": RunnablePassthrough()} | prompt
            promptValue: ChatPromptValue = cast(
                ChatPromptValue, await retrieval_chain.ainvoke(question)
            )
            m = promptValue.to_messages()[-1]
            # logger.debug(f"Retrieved mess age: {type(mm)} {len(mm)} {mm}")
            messages[-1] = ChatMsg(role="user", content=m.content)  # pyright: ignore [reportArgumentType]
            # TODO: clean up later

        if llm_name is None:
            llm_name = bot_cfg.model.name

        return await self.query_llm(llm_name, messages)

    def get_models(self) -> Models:
        return Models(llms=list(self.config.llm_models.keys()), bots=list(self.bots.keys()))

    def open_db(self):
        return open_sqlite_db(ensure_dir(self.config.state_path) / "state.db")

    def process_files(self):
        file_states = FileStates()
        for bot in self.bots.values():
            if bot.rag is None:
                continue
            for glob in bot.rag.files:
                for file in sorted(glob.get_matching_files()):
                    fstate = file_states.add_file(file)
                    fstate.collections[bot.rag.vector_db_collection] = FileTransition(None, True)

        with self.open_db() as conn:
            if not check_all_tables_exist(conn):
                create_tables(conn)
            latest = sorted(select_all_active_sources(conn), key=lambda s: s[0].absolute_path)

            if latest:
                sources, actions, collections = zip(*latest, strict=False)
                for i in range(len(sources)):
                    source = sources[i]
                    file_state = file_states.add_file(source.absolute_path)

                    for c in collections[i]:
                        if c.action == "delete":
                            continue
                        if c.collection not in file_state.collections:
                            file_state.collections[c.collection] = FileTransition(None, False)
                        file_state.collections[c.collection].present_before_sha256 = actions[
                            i
                        ].sha256

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
            logger.debug(f"Processing {state.path}")
            if pending_uploads:
                logger.debug(f"Pending uploads: {pending_uploads}")
                try:
                    chunks = load_document_into_chunks(state.path)
                    if len(chunks) == 0:
                        logger.debug(f"No chunks for {state.path}")
                        continue
                    action = self.store_action(source, len(chunks), state)
                    for collection, action_type in pending_uploads:
                        db = get_vector_collection(self.config, collection)
                        if action_type == "update":
                            db.delete(where={"source": str(state.path)})
                        db.add_documents(chunks)
                        self.store_collection_action(action, collection, action_type)
                except Exception as e:
                    logger.warning(f"Error loading document {state.path}: {e}")
                    logger.warning(traceback.format_exc())
                    continue
            if deletes:
                logger.debug(f"Deletes: {deletes}")
                if action is None:
                    action = self.store_action(source, 0, state)
                for collection in deletes:
                    db = get_vector_collection(self.config, collection)
                    db.delete(where={"source": str(state.path)})
                    self.store_collection_action(action, collection, "delete")

    def store_source(self, path: Path) -> RagSource:
        with self.open_db() as conn:
            sources = RagSource.select(conn, absolute_path=path)
            if len(sources) == 0:
                source = RagSource(absolute_path=path)
                source.save(conn)
                conn.commit()
                logger.debug(f"Stored source {source}")
                return source
            else:
                assert len(sources) == 1, f"Multiple sources for {path}"
                logger.debug(f"Found source {sources[0]}")
                return sources[0]

    def store_action(self, source: RagSource, n_chunks: int, state: FileState) -> RagAction:
        with self.open_db() as conn:
            action = RagAction(
                source_id=source.source_id,
                timestamp=datetime.now(tz=UTC),
                n_chunks=n_chunks,
                error=None,
                sha256=state.sha256(),
            )
            action.save(conn)
            conn.commit()
            logger.debug(f"Stored action {action}")
            return action

    def store_collection_action(
        self, action: RagAction, collection: str, action_type: ActionType
    ) -> RagActionCollection:
        with self.open_db() as conn:
            collection_action = RagActionCollection(
                action_id=action.action_id,
                action=action_type,
                collection=collection,
                timestamp=datetime.now(tz=UTC),
            )
            collection_action.insert(conn)
            conn.commit()
            logger.debug(f"Stored collection action {collection_action}")
            return collection_action

    def run(self):
        pass
