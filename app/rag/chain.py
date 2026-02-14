"""RAG chain — LCEL-based retrieval with temporal context and business rules."""

import os
import logging
from datetime import datetime
from typing import Optional

import pytz
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.config import get_settings
from app.rag.embeddings import get_embeddings, get_llm
from app.rag.loader import load_products_as_documents
from app.rag.prompts import SYSTEM_PROMPT_TEMPLATE, WHATSAPP_SYSTEM_PROMPT

settings = get_settings()
logger = logging.getLogger(__name__)
tz = pytz.timezone(settings.TIMEZONE)

# ChromaDB persistent directory
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "chroma_db")


def get_vector_store():
    """Get or create the Chroma vector store."""
    os.makedirs(CHROMA_DIR, exist_ok=True)
    embeddings = get_embeddings()
    return Chroma(
        collection_name="products",
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )


def index_products(db: Session, upload_id: Optional[int] = None):
    """Index products from DB into the vector store."""
    logger.info("Starting product indexing...")
    documents = load_products_as_documents(db, upload_id)

    if not documents:
        logger.warning("No documents to index")
        return 0

    # Split documents for better retrieval
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " "],
    )
    split_docs = text_splitter.split_documents(documents)

    # Clear existing data and re-index
    vector_store = get_vector_store()

    # Delete existing collection data
    try:
        existing = vector_store.get()
        if existing and existing.get("ids"):
            vector_store.delete(ids=existing["ids"])
    except Exception:
        pass

    # Add new documents in batches
    batch_size = 100
    for i in range(0, len(split_docs), batch_size):
        batch = split_docs[i:i + batch_size]
        vector_store.add_documents(batch)

    logger.info(f"Indexed {len(split_docs)} document chunks from {len(documents)} products")
    return len(split_docs)


def _format_docs(docs) -> str:
    """Format retrieved documents into a context string."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def query_rag(question: str, use_whatsapp_format: bool = False) -> str:
    """Query the RAG system with temporal awareness using LCEL."""
    now = datetime.now(tz)
    current_date = now.strftime("%d/%m/%Y")
    current_time = now.strftime("%H:%M")

    vector_store = get_vector_store()

    # Check if we have any documents
    try:
        collection_data = vector_store.get()
        if not collection_data or not collection_data.get("ids"):
            return "⚠️ Nenhum dado de produtos encontrado. Por favor, faça upload de uma planilha primeiro."
    except Exception:
        return "⚠️ Erro ao acessar a base de dados de produtos."

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 60},
    )

    template = WHATSAPP_SYSTEM_PROMPT if use_whatsapp_format else SYSTEM_PROMPT_TEMPLATE

    # Fill temporal placeholders
    filled_template = template.replace("{current_date}", current_date).replace("{current_time}", current_time)

    prompt = ChatPromptTemplate.from_template(filled_template)

    llm = get_llm()

    # LCEL chain: retrieve → format → prompt → llm → parse
    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    try:
        result = chain.invoke(question)
        return result
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        return f"❌ Erro ao processar pergunta: {str(e)}"
