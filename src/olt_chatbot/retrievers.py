"""Code for the document retriever."""

import itertools
import pickle
from collections.abc import Iterator

from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from olt_chatbot import config
from olt_chatbot.document_parsing import (
    get_docs_from_url,
    read_pdfs_from_fagstoff_folder,
)
from olt_chatbot.llm_models import EMBEDDING_MODELS

EMBEDDING = EMBEDDING_MODELS["text-embedding-3-large"]


def update_retriever_databases() -> None:
    """Update the retriever databases."""
    all_docs = itertools.chain(
        get_docs_from_url("https://olympiatoppen.no/", max_depth=100),
        get_docs_from_url("https://olt-skala.nif.no/", max_depth=100),
        read_pdfs_from_fagstoff_folder(),
    )
    write_docstores_to_disk(all_docs)


def write_docstores_to_disk(docs: Iterator[Document]) -> None:
    """Store a vector db and BM25 retriever to disk."""
    text_splitter = RecursiveCharacterTextSplitter(
        # Set a really small chunk size, just to show.
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
    )

    # Make two independent interators, so we can feed one to each of the indexers.
    docs1, docs2 = itertools.tee(docs, 2)
    logger.info("Creating vector retriever")
    Chroma.from_documents(
        filter_complex_metadata(text_splitter.split_documents(docs1)),
        embedding=EMBEDDING,
        persist_directory=config.CHROMA_DB_PATH,
    )

    logger.info("Creating BM25 retriever")
    bm25_retriever = BM25Retriever.from_documents(text_splitter.split_documents(docs2))
    with config.BM25_RETRIEVER_PATH.open("wb") as file:
        pickle.dump(bm25_retriever, file)


def load_retriever_from_disk(k: int = 15) -> BaseRetriever:
    """Load retriever(s) from disk."""
    # Load Chroma db from disk
    logger.debug("Loading retriever from disk")
    vectordb = Chroma(
        persist_directory=config.CHROMA_DB_PATH, embedding_function=EMBEDDING
    )
    vector_retriever = vectordb.as_retriever(search_kwargs={"k": k})

    # Load BM25 retriever from disk
    with config.BM25_RETRIEVER_PATH.open("rb") as file:
        bm25_retriever = pickle.load(file)  # noqa: S301
        bm25_retriever.k = k

    # ensemble_retriever = EnsembleRetriever(
    #     retrievers=[bm25_retriever, vector_retriever], weights=[0.4, 0.6]
    # )
    return vector_retriever
