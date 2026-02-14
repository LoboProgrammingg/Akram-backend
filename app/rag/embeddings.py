"""RAG embeddings configuration — supports OpenAI and Gemini."""

from app.config import get_settings

settings = get_settings()


def get_embeddings():
    """Get the configured embeddings model."""
    if settings.AI_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            model="text-embedding-3-small",
        )
    else:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            google_api_key=settings.GEMINI_API_KEY,
            model="models/gemini-embedding-001",
        )


def get_llm():
    """Get the configured LLM model."""
    if settings.AI_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.1,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            google_api_key=settings.GEMINI_API_KEY,
            model="gemini-2.5-flash",
            temperature=0.1,
        )
