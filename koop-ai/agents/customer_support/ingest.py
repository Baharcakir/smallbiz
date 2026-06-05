"""
Dokümanları ChromaDB vektör deposuna yükle.
Çalıştır: python agents/customer_support/ingest.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


def ingest_documents():
    """Docs klasöründeki tüm .txt dosyalarını ChromaDB'ye yükle."""
    print("📚 Dokümanlar yükleniyor...")

    loader = DirectoryLoader(
        DOCS_DIR,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()
    print(f"   {len(documents)} dosya bulundu.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(documents)
    print(f"   {len(chunks)} chunk oluşturuldu.")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name="koop_ai_docs",
    )
    print(f"✅ {len(chunks)} chunk ChromaDB'ye kaydedildi → {CHROMA_DIR}")
    return vectorstore


if __name__ == "__main__":
    ingest_documents()
