"""
RAG (Retrieval-Augmented Generation) service module.

Adapted from the user's Jupyter notebook. Handles:
  - PDF loading and text splitting
  - Embedding with HuggingFace (BAAI/bge-small-en-v1.5)
  - Vector storage with ChromaDB (per-session)
  - Question answering via Groq LLM (Llama 3.3 70B) + LangChain chain
"""

import os
import shutil
import time

from django.conf import settings

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
LLM_MODEL_NAME = "llama-3.3-70b-versatile"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RETRIEVER_K = 10
BATCH_SIZE = 20

# ---------------------------------------------------------------------------
# Prompt template (adapted from notebook)
# ---------------------------------------------------------------------------
SYSTEM_TEMPLATE = (
    "You are an intelligent document assistant. "
    "Your job is to answer questions using ONLY the provided context from the user's uploaded PDF documents.\n"
    "Use the following context to answer questions.\n"
    "Be as detailed as possible, but don't make up any information that's not from the context.\n"
    "If you don't know an answer, say you don't know.\n"
    "Format your answers clearly using paragraphs and bullet points where appropriate.\n\n"
    "{context}"
)

# ---------------------------------------------------------------------------
# Singleton-ish embedding model (expensive to load, reuse across requests)
# ---------------------------------------------------------------------------
_embedding_model = None


def get_embedding_model():
    """Return (and lazily initialise) the shared HuggingFace embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
        )
    return _embedding_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chroma_path(session_id: str) -> str:
    """Return the on-disk path for a session's ChromaDB store."""
    base = getattr(settings, "CHROMA_DB_DIR", settings.BASE_DIR / "chroma_stores")
    os.makedirs(base, exist_ok=True)
    return str(os.path.join(base, session_id))


def _build_prompt_template() -> ChatPromptTemplate:
    """Build the system + human chat prompt template."""
    system_prompt = SystemMessagePromptTemplate(
        prompt=PromptTemplate(
            input_variables=["context"],
            template=SYSTEM_TEMPLATE,
        )
    )
    human_prompt = HumanMessagePromptTemplate(
        prompt=PromptTemplate(
            input_variables=["question"],
            template="{question}",
        )
    )
    return ChatPromptTemplate(
        input_variables=["context", "question"],
        messages=[system_prompt, human_prompt],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_pdfs(pdf_paths: list, session_id: str):
    """
    Load PDFs, split into chunks, embed, and persist to ChromaDB.

    Parameters
    ----------
    pdf_paths : list[str]
        Absolute paths to uploaded PDF files.
    session_id : str
        Unique session identifier (used as ChromaDB collection directory).

    Returns
    -------
    int
        Total number of document chunks stored.
    """
    # 1. Load all PDFs
    all_documents = []
    for path in pdf_paths:
        loader = PyPDFLoader(path)
        documents = loader.load()
        all_documents.extend(documents)

    if not all_documents:
        raise ValueError("No text could be extracted from the uploaded PDFs.")

    # 2. Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(all_documents)

    if not chunks:
        raise ValueError("Text splitting produced zero chunks. The PDFs may be empty or image-only.")

    # 3. Get embedding model
    embedding_fn = get_embedding_model()

    # 4. Create / populate ChromaDB in batches (adapted from notebook)
    persist_dir = _chroma_path(session_id)

    # If there's already a store for this session, remove it first
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

    vector_db = None
    num_batches = (len(chunks) - 1) // BATCH_SIZE + 1

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        if i == 0:
            vector_db = Chroma.from_documents(
                documents=batch,
                embedding=embedding_fn,
                persist_directory=persist_dir,
            )
        else:
            vector_db.add_documents(documents=batch)
        # Small pause to be kind to the embedding model
        time.sleep(0.2)

    return len(chunks)


def ask_question(question: str, session_id: str, groq_api_key: str) -> str:
    """
    Run the RAG chain: retrieve relevant chunks → prompt → LLM → answer.

    Parameters
    ----------
    question : str
        The user's question.
    session_id : str
        Session identifier to locate the correct ChromaDB store.
    groq_api_key : str
        Groq API key for the LLM.

    Returns
    -------
    str
        The LLM's answer.
    """
    persist_dir = _chroma_path(session_id)
    if not os.path.exists(persist_dir):
        return "No documents have been uploaded yet. Please go back and upload your PDFs first."

    # Load existing ChromaDB
    embedding_fn = get_embedding_model()
    vector_db = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_fn,
    )

    # Build retriever
    retriever = vector_db.as_retriever(search_kwargs={"k": RETRIEVER_K})

    # Build LLM
    llm = ChatGroq(
        model=LLM_MODEL_NAME,
        temperature=0,
        groq_api_key=groq_api_key,
    )

    # Build chain (same pattern as the notebook)
    prompt_template = _build_prompt_template()

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke(question)
    return answer


def clear_session_data(session_id: str):
    """Delete the ChromaDB store and uploaded files for a session."""
    persist_dir = _chroma_path(session_id)
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

    # Also remove uploaded PDFs for this session
    media_session_dir = os.path.join(settings.MEDIA_ROOT, "pdfs", session_id)
    if os.path.exists(media_session_dir):
        shutil.rmtree(media_session_dir)
