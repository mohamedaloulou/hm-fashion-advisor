"""
ingest.py  —  One-time ingestion script
Reads read_file.json → builds LangChain Documents → stores in ChromaDB.

Run once before starting the Streamlit app:
    python ingest.py
"""

import json
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

# ── Config (must match app.py) ─────────────────────────────────────────────────
JSON_PATH       = "./ready_file.json"
CHROMA_PATH     = "./chroma_db"
COLLECTION_NAME = "hm_products"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE      = 500   # tune down if you hit memory limits


def load_documents(json_path: str) -> list[Document]:
    """
    Convert each row in read_file.json into a LangChain Document.

    Your JSON structure:
      [
        {
          "text": "Product: Strap top. Type: ...",   ← becomes page_content
          "metadata": { "prod_name": ..., ... }       ← becomes metadata
        },
        ...
      ]

    LangChain Document = page_content (str) + metadata (dict).
    This is the native unit for every LangChain vectorstore operation.
    """
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


def ingest(docs: list[Document]) -> None:
    """
    Embed and store documents in ChromaDB via LangChain.

    LangChain handles:
      - Calling the embedding model in batches
      - Creating / opening the ChromaDB collection
      - Persisting to disk at CHROMA_PATH

    Equivalent of the old manual chromadb.PersistentClient().get_or_create_collection()
    + collection.add(documents=..., embeddings=..., metadatas=...) workflow.
    """
    print(f"⏳ Loading embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print(f"⏳ Ingesting into ChromaDB at {CHROMA_PATH} ...")

    # Process in batches to avoid OOM on large datasets
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        if i == 0:
            # First batch: create the collection
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                persist_directory=CHROMA_PATH,
            )
        else:
            # Subsequent batches: add to existing collection
            vectorstore.add_documents(batch)
        print(f"   → Ingested {min(i + BATCH_SIZE, len(docs))} / {len(docs)}")

    print(f"✅ Done! Collection '{COLLECTION_NAME}' ready in {CHROMA_PATH}")


if __name__ == "__main__":
    documents = load_documents(JSON_PATH)
    ingest(documents)
