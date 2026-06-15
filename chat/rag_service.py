"""
RAG (Retrieval-Augmented Generation) service module.

Adapted from the user's Jupyter notebook. Handles:
  - PDF loading and text splitting
  - Embedding with FastEmbed (highly optimized, runs locally)
  - Vector storage with ChromaDB (per-session basis)
  - Question answering via Groq LLM (Llama 3.3 70B) + LangChain chain
"""

import os
import shutil
import time

from django.conf import settings

# Langchain imports for document processing and RAG pipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
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
# The model used to convert text into vector embeddings. 
# BAAI/bge-small-en-v1.5 is a highly efficient model for semantic search.
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# The Groq model we will query. Llama 3.3 70B provides excellent reasoning.
LLM_MODEL_NAME = "llama-3.3-70b-versatile"

# How large each chunk of text should be when splitting the PDF.
CHUNK_SIZE = 500

# How many characters should overlap between chunks (preserves context across boundaries).
CHUNK_OVERLAP = 50

# How many relevant document chunks to retrieve for each question.
RETRIEVER_K = 10

# Batch size for adding documents to ChromaDB to avoid memory spikes.
BATCH_SIZE = 20

# ---------------------------------------------------------------------------
# Prompt template (adapted from notebook)
# ---------------------------------------------------------------------------
# This template tells the LLM how to behave. It strictly instructs the LLM to 
# use ONLY the provided context and not hallucinate answers.
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
# We store the model in a global variable so it is loaded only once per server process.
# Loading models repeatedly on every request would severely degrade performance.
_embedding_model = None


def get_embedding_model():
    """Return (and lazily initialise) the shared HuggingFace cloud embedding model."""
    global _embedding_model
    if _embedding_model is None:
        # HuggingFace Endpoint Embeddings run on Hugging Face's cloud servers,
        # completely avoiding the Out Of Memory crashes on Render.
        hf_token = getattr(settings, "HF_TOKEN", "")
        if not hf_token:
            raise ValueError("HF_TOKEN environment variable is not set. Please configure it in your environment.")
            
        _embedding_model = HuggingFaceEndpointEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            task="feature-extraction",
            huggingfacehub_api_token=hf_token,
        )
    return _embedding_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chroma_path(session_id: str) -> str:
    """
    Return the on-disk path for a session's ChromaDB store.
    Each user gets their own isolated vector database folder based on their session ID.
    """
    base = getattr(settings, "CHROMA_DB_DIR", settings.BASE_DIR / "chroma_stores")
    os.makedirs(base, exist_ok=True)
    return str(os.path.join(base, session_id))


def _build_prompt_template() -> ChatPromptTemplate:
    """
    Build the system + human chat prompt template.
    Langchain uses these templates to structure the conversation properly 
    for chat models.
    """
    # The system prompt receives the 'context' (the retrieved PDF chunks)
    system_prompt = SystemMessagePromptTemplate(
        prompt=PromptTemplate(
            input_variables=["context"],
            template=SYSTEM_TEMPLATE,
        )
    )
    # The human prompt receives the actual 'question' asked by the user
    human_prompt = HumanMessagePromptTemplate(
        prompt=PromptTemplate(
            input_variables=["question"],
            template="{question}",
        )
    )
    # Combine them into a single ChatPromptTemplate
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
    # We iterate over the file paths, load them using Langchain's PyPDFLoader
    all_documents = []
    for path in pdf_paths:
        loader = PyPDFLoader(path)
        documents = loader.load()
        all_documents.extend(documents)

    if not all_documents:
        raise ValueError("No text could be extracted from the uploaded PDFs.")

    # 2. Split into chunks
    # We split large documents into smaller chunks so that the vector search
    # can find specific relevant paragraphs rather than returning entire books.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(all_documents)

    if not chunks:
        raise ValueError("Text splitting produced zero chunks. The PDFs may be empty or image-only.")

    # 3. Get embedding model
    # Convert text chunks into numerical vectors (embeddings)
    embedding_fn = get_embedding_model()

    # 4. Create / populate ChromaDB in batches
    persist_dir = _chroma_path(session_id)

    # If there's already a store for this session, remove it first to avoid mixing old/new data.
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

    vector_db = None
    num_batches = (len(chunks) - 1) // BATCH_SIZE + 1

    # We add documents in batches. This prevents out-of-memory errors on large PDFs.
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        if i == 0:
            # On the first batch, create the database
            vector_db = Chroma.from_documents(
                documents=batch,
                embedding=embedding_fn,
                persist_directory=persist_dir,
            )
        else:
            # On subsequent batches, add to the existing database
            vector_db.add_documents(documents=batch)
        # Small pause to be kind to the system's memory and CPU
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

    # Load existing ChromaDB from disk
    embedding_fn = get_embedding_model()
    vector_db = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_fn,
    )

    # Build retriever: this will take a query, convert it to an embedding, 
    # and find the K most similar chunks in the database.
    retriever = vector_db.as_retriever(search_kwargs={"k": RETRIEVER_K})

    # Build LLM client to talk to Groq's fast inference API
    llm = ChatGroq(
        model=LLM_MODEL_NAME,
        temperature=0,  # Temperature 0 makes the model factual and deterministic
        groq_api_key=groq_api_key,
    )

    # Build the langchain pipeline
    prompt_template = _build_prompt_template()

    # The Chain does the following:
    # 1. Takes the "question" and passes it to the retriever to get "context" chunks.
    # 2. Passes both "context" and "question" into the prompt_template.
    # 3. Sends the formatted prompt to the LLM.
    # 4. Parses the LLM's response as a plain string.
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )

    # Execute the chain
    answer = chain.invoke(question)
    return answer


def clear_session_data(session_id: str):
    """Delete the ChromaDB store and uploaded files for a session."""
    # Delete vector database directory
    persist_dir = _chroma_path(session_id)
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

    # Delete the actual uploaded PDFs
    media_session_dir = os.path.join(settings.MEDIA_ROOT, "pdfs", session_id)
    if os.path.exists(media_session_dir):
        shutil.rmtree(media_session_dir)
