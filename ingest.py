"""
ingest.py  —  One-time ingestion script
Reads ready_file.json → builds LangChain Documents → stores in Pinecone.

Run once locally before deploying:
    python ingest.py

Requirements:
    PINECONE_API_KEY must be set in your .env file or environment.
"""

import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
JSON_PATH       = "./ready_file.json"
INDEX_NAME      = "hm-products"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DIMENSION       = 384        # all-MiniLM-L6-v2 output size
METRIC          = "cosine"
BATCH_SIZE      = 100        # Pinecone free tier: keep batches small
PINECONE_CLOUD  = "aws"
PINECONE_REGION = "us-east-1"


def load_documents(json_path: str) -> list[Document]:
    raw = json.loads(Path(json_path).read_text(encoding="utf-8"))
    docs = []
    for row in raw:
        docs.append(
            Document(
                page_content=row["text"],
                metadata=row.get("metadata", {}),
            )
        )
    print(f"✅ Loaded {len(docs)} documents from {json_path}")
    return docs


def create_index_if_not_exists(pc: Pinecone) -> None:
    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME in existing:
        print(f"✅ Index '{INDEX_NAME}' already exists — skipping creation.")
        return

    print(f"⏳ Creating Pinecone index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric=METRIC,
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
    )
    # Wait for index to be ready
    while not pc.describe_index(INDEX_NAME).status["ready"]:
        print("   Waiting for index to be ready...")
        time.sleep(2)
    print(f"✅ Index '{INDEX_NAME}' is ready.")


def ingest(docs: list[Document]) -> None:
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found. Add it to your .env file.")

    pc = Pinecone(api_key=api_key)
    create_index_if_not_exists(pc)

    print(f"⏳ Loading embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print(f"⏳ Ingesting {len(docs)} documents into Pinecone in batches of {BATCH_SIZE}...")
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i: i + BATCH_SIZE]
        PineconeVectorStore.from_documents(
            documents=batch,
            embedding=embeddings,
            index_name=INDEX_NAME,
            pinecone_api_key=api_key,
        )
        print(f"   → Ingested {min(i + BATCH_SIZE, len(docs))} / {len(docs)}")

    print(f"✅ Done! {len(docs)} documents stored in Pinecone index '{INDEX_NAME}'.")


if __name__ == "__main__":
    documents = load_documents(JSON_PATH)
    ingest(documents)
