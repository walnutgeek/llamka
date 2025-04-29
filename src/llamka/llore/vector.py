# TODO: implement vectorization of documents using croma db and langchain.
# Obtain list of files from config.
# For each file, extract the text according and vectorize it using langchain.
# Store the vectorized text in a croma db persidted in the data/chroma directory.

import os
import sys
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, UnstructuredEPubLoader
from langchain_huggingface import HuggingFaceEmbeddings

from llamka.llore.config import Config, load_config

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def get_document_loader(file_path: Path):
    """Get appropriate document loader based on file extension"""
    if file_path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(file_path))
    elif file_path.suffix.lower() == ".epub":
        return UnstructuredEPubLoader(str(file_path))
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")


def get_vector_db(config: Config):
    embeddings = HuggingFaceEmbeddings(
        model_name=config.vectorization.embedding.model_name,  # "all-MiniLM-L6-v2",
        model_kwargs=config.vectorization.embedding.model_params,  # {'device': 'cpu'},
        encode_kwargs=config.vectorization.embedding.encode_params,  # {'normalize_embeddings': True}
    )

    # Initialize ChromaDB
    db = Chroma(
        persist_directory=config.vectorization.vector_db.ensure_dir(),
        embedding_function=embeddings,
        collection_name=config.vectorization.vector_db.collection_name,
    )
    return db


def process_documents():
    """Process documents from config and store vectors in ChromaDB"""
    # Load config
    config = load_config("data/config.json")

    # Create data/chroma directory if it doesn't exist

    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, length_function=len
    )
    db = get_vector_db(config)

    # Process each file
    for file_path in config.get_paths():
        try:
            # Load document
            loader = get_document_loader(file_path)
            documents = loader.load()

            # Split text into chunks
            splits = text_splitter.split_documents(documents)

            if len(splits) == 0:
                print(f"No splits for {file_path}")
                continue

            # Add to vector store}
            db.delete(where={"source": str(file_path)})
            db.add_documents(splits)

            print(f"Processed {file_path}")

        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Error processing {file_path}: {str(e)}")


def run_proximity_search(query: str, k: int = 4) -> list[str]:
    """
    Run a proximity search against the vector database.

    Args:
        query: The search query text
        k: Number of results to return (default 4)

    Returns:
        List of relevant document content strings
    """
    config = load_config("data/config.json")
    # Initialize embeddings and ChromaDB with same settings
    db = get_vector_db(config)

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
        process_documents()
