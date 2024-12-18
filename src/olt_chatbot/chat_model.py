"""Code for the LangChain Question-Answer chain."""

from operator import itemgetter
from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from loguru import logger
from pydantic import BaseModel, Field

from olt_chatbot.llm_models import LLM_GENERATORS
from olt_chatbot.retrievers import load_retriever_from_disk


class CitedAnswer(BaseModel):
    """Answer the user question based only on the given sources, and cite the sources used."""  # noqa:E501

    answer: str = Field(
        ...,
        description=(
            "The answer to the user question, which is based only on the given sources."
        ),
    )
    citations: list[str] = Field(
        ...,
        description="The reference of the SPECIFIC sources which justify the answer.",
    )


# Gammelt"


def get_chain_with_history(
    model_name: str = "gpt-4o",
) -> Runnable[dict[str, Any], dict[str, Any]]:
    """Create a chat model with history."""
    logger.debug(f"Creating chat model with {model_name}")

    def format_docs(docs: list[Document]) -> str:
        return "\n\n".join(
            f"Reference: {doc.metadata['source']}\nContent: {doc.page_content}"
            for doc in docs
        )

    llm = LLM_GENERATORS[model_name]
    retriever = load_retriever_from_disk()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a helpful AI assistant working at Olympiatoppen. "
                    "You answer questions in Norwegian. "
                ),
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            (
                "human",
                (
                    "You are an assistant for question-answering tasks. "
                    "Given a user question and some context, answer the question."
                    "If you don't know the answer, just say that you "
                    "don't know.\n\n"
                    "Context: {context}\n\n"
                ),
            ),
            ("human", "{question}"),
        ]
    )

    rag_chain_from_docs = (
        RunnablePassthrough.assign(
            context=itemgetter("context") | RunnableLambda(format_docs)
        )
        | prompt
        | llm.with_structured_output(CitedAnswer)
    )
    return RunnablePassthrough.assign(
        context=itemgetter("question") | retriever
    ).assign(cited_answer=rag_chain_from_docs)


def get_chain_without_history(
    llm_name: str = "gpt-4o",
) -> Runnable[str, dict[str, Any]]:
    """Get the QA chain for Cited Answers."""

    def format_docs_with_id(docs: list[Document]) -> str:
        """Format the documents with an enumerated ID."""
        formatted = [
            (f"Source ID: {i}\nArticle Snippet: {doc.page_content}")
            for i, doc in enumerate(docs)
        ]
        return "\n\n".join(formatted)

    llm = LLM_GENERATORS[llm_name]
    llm_with_tool = llm.with_structured_output(CitedAnswer)
    retriever = load_retriever_from_disk(k=20)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a helpful AI assistant. You answer question in Norwegian."
                    "You are working at Olympiatoppen."
                    "Given a user question and some context, answer the user question."
                    "If you dont know the answer, just say you dont know.\n\n"
                    "Here is the context: \n\n{context}"
                ),
            ),
            ("human", "{question}"),
        ]
    )

    formatted_docs = itemgetter("docs") | RunnableLambda(format_docs_with_id)
    answer_chain = prompt | llm_with_tool
    return (
        RunnableParallel(question=RunnablePassthrough(), docs=retriever)
        .assign(context=formatted_docs)
        .assign(cited_answer=answer_chain)
        .pick(["cited_answer", "docs"])
    )
