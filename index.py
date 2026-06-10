"""Stage 3: Embedding + Vector Store.

Embeds every chunk with a sentence-transformers model and stores the vectors
in a persistent ChromaDB collection. Run this once (or after changing the
documents) to build the index that query.py reads from.

Embedding model: all-MiniLM-L6-v2
  - 384-dimensional, fast, runs locally with no API cost
  - Strong general-purpose semantic similarity; well-suited to short English
    fan-guide prose. See planning.md for the production-tradeoff discussion.
"""

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from ingest import build_chunks

EMBED_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "the_boys_guide"
CHROMA_DIR = str(Path(__file__).parent / "chroma_store")


def get_collection(reset: bool = False):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def build_index():
    print(f"Loading embedding model: {EMBED_MODEL} ...")
    model = SentenceTransformer(EMBED_MODEL)

    print("Chunking documents ...")
    chunks = build_chunks()
    if not chunks:
        raise SystemExit("No chunks produced — is the documents/ folder empty?")

    print(f"Embedding {len(chunks)} chunks ...")
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    collection = get_collection(reset=True)
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[{"source": c["source"]} for c in chunks],
    )
    print(f"Indexed {collection.count()} chunks into '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    build_index()
