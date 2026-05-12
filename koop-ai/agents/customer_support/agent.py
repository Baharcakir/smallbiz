"""
Agent 1 — Müşteri Destek (RAG)
Gemini 1.5 Flash + LangChain + ChromaDB
"""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import google.generativeai  # noqa — LangChain google genai bağımlılığı

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

SYSTEM_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""Sen Hatay Kadınlar Kooperatifi'nin yardımsever müşteri hizmetleri asistanısın.
Sana verilen belgelerdeki bilgileri kullanarak müşteri sorularını nazik, sade ve anlaşılır Türkçe ile yanıtla.
Eğer yanıtı belgede bulamazsan, "Bu konuda size yardımcı olamıyorum, lütfen müşteri hizmetlerimizi arayınız." de.
Asla uydurma bilgi verme.

Belgeler:
{context}

Müşteri sorusu: {question}

Yanıt:"""
)


@lru_cache(maxsize=1)
def _get_vectorstore():
    """ChromaDB bağlantısını bir kez kur ve cache'le."""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name="koop_ai_docs",
    )


def build_rag_chain():
    """RAG zinciri oluştur."""
    vectorstore = _get_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.2,
        convert_system_message_to_human=True,
    )
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": SYSTEM_PROMPT},
    )


def answer_customer_query(query: str) -> dict:
    """
    Müşteri sorusunu yanıtla.
    Returns: {"answer": str, "sources": list[str]}
    """
    chain = build_rag_chain()
    result = chain.invoke({"query": query})

    sources = []
    for doc in result.get("source_documents", []):
        source = doc.metadata.get("source", "")
        if source and source not in sources:
            sources.append(os.path.basename(source))

    return {
        "answer": result["result"],
        "sources": sources,
    }
