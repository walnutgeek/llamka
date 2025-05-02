# TODO: implement vectorization of documents using croma db and langchain.
# Obtain list of files from config.
# For each file, extract the text according and vectorize it using langchain.
# Store the vectorized text in a croma db persidted in the data/chroma directory.

import os
import sys
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings

from llamka.llore.config import Config, load_config

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def get_document_loader(file_path: Path):
    """Get appropriate document loader based on file extension"""
    if file_path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(file_path))
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")


def get_vector_collection(config: Config, collection: str) -> Chroma:
    vector_db = config.vector_db
    embeddings = HuggingFaceEmbeddings(
        model_name=vector_db.embeddings.model_name,  # "all-MiniLM-L6-v2",
        model_kwargs=vector_db.embeddings.model_params,  # {'device': 'cpu'},
        encode_kwargs=vector_db.embeddings.encode_params,  # {'normalize_embeddings': True}
    )

    # Initialize ChromaDB
    return Chroma(
        persist_directory=vector_db.ensure_dir(),
        embedding_function=embeddings,
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


def run_proximity_search(query: str, k: int = 4) -> list[str]:
    """
    Run a proximity search against the vector database.

    Args:
        query: The search query text
        k: Number of results to return (default 4)

    Returns:
        List of relevant document content strings
    """
    config, _ = load_config("data/config.json")
    # Initialize embeddings and ChromaDB with same settings
    db = get_vector_collection(config, "documents")

    # Run similarity search
    results = db.similarity_search(query, k=k)

    # Extract and return the content from results
    return [doc.page_content for doc in results]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        rr = run_proximity_search(" ".join(sys.argv[1:]), 5)
        for r in rr:
            print("-" * 10)
            print(r)
    else:
        print("No query provided")
