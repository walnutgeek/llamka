import logging
import os
from collections.abc import Generator
from pathlib import Path

import chromadb.config
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings

from botglue.llore.config import Config
from botglue.misc import ensure_dir

os.environ["TOKENIZERS_PARALLELISM"] = "false"

logger = logging.getLogger(__name__)


def get_document_loader(file_path: Path):
    """Get appropriate document loader based on file extension"""
    if file_path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(file_path))
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")


def gen_matching_snapshots(cache_dir: Path, model_name: str) -> Generator[str, None, None]:
    for model_dir in cache_dir.glob(f"*{model_name}"):
        if (model_dir / "snapshots").is_dir():
            for snapshot_dir in model_dir.glob("snapshots/*"):
                if snapshot_dir.is_dir() and len(snapshot_dir.name) == 40:
                    yield f"{model_dir.name}/snapshots/{snapshot_dir.name}"


def get_vector_collection(config: Config, collection: str) -> Chroma:
    db_cfg = config.vector_db
    emb_cfg = db_cfg.embeddings

    def load_embeddings(name: str = emb_cfg.model_name) -> HuggingFaceEmbeddings:
        return HuggingFaceEmbeddings(
            model_name=name,  # "all-MiniLM-L6-v2",
            model_kwargs=emb_cfg.model_params,  # {'device': 'cpu'},
            encode_kwargs=emb_cfg.encode_params,  # {'normalize_embeddings': True}
        )

    if emb_cfg.cache_model:
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(ensure_dir(config.hf_hub_dir).absolute())
        if emb_cfg.cache_path is None:
            embeddings = load_embeddings()
        else:
            try:
                resolved_path = config.hf_hub_dir / emb_cfg.cache_path
                if not resolved_path.is_dir():
                    raise FileNotFoundError(
                        f"Cache path {resolved_path} not found. Possible options: {list(gen_matching_snapshots(config.hf_hub_dir, emb_cfg.model_name))}"
                    )
                embeddings = load_embeddings(str(config.hf_hub_dir / emb_cfg.cache_path))
            except Exception as e:
                logger.error(f"Error loading embeddings from cache: {e}")
                logger.info(f"Loading embeddings from hf site: {emb_cfg.model_name}")
                embeddings = load_embeddings()

    client_settings = chromadb.config.Settings(
        is_persistent=True,
        persist_directory=str(ensure_dir(db_cfg.dir)),
        anonymized_telemetry=False,
    )
    return Chroma(
        client_settings=client_settings,
        embedding_function=embeddings,  # pyright: ignore[reportPossiblyUnboundVariable]
        collection_name=collection,
    )


def load_document_into_chunks(file_path: Path):
    """Load document into chunks"""
    loader = get_document_loader(file_path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, length_function=len
    )
    splits = text_splitter.split_documents(documents)
    return splits
