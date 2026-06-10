

from pathlib import Path

CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
DOCS_DIR = Path(__file__).parent / "documents"


def load_documents(docs_dir: Path = DOCS_DIR) -> list[dict]:
    """Read every supported file in docs_dir into {source, text} records."""
    records = []
    for path in sorted(docs_dir.iterdir()):
        if path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8")
        elif path.suffix.lower() == ".pdf":
            text = _read_pdf(path)
        else:
            continue  # skip .gitkeep and anything else
        records.append({"source": path.name, "text": text})
    return records


def _read_pdf(path: Path) -> str:
    import pdfplumber  # only imported if a .pdf is actually present

    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character windows."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    chunks = []
    start = 0
    step = size - overlap
    while start < len(text):
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def build_chunks(docs_dir: Path = DOCS_DIR) -> list[dict]:
    """Load all documents and return a flat list of chunk records.

    Each record: {id, text, source}. The id is stable across runs so the
    vector store can upsert deterministically.
    """
    chunk_records = []
    for doc in load_documents(docs_dir):
        for i, chunk in enumerate(chunk_text(doc["text"])):
            chunk_records.append(
                {
                    "id": f"{doc['source']}::chunk{i}",
                    "text": chunk,
                    "source": doc["source"],
                }
            )
    return chunk_records


if __name__ == "__main__":
    chunks = build_chunks()
    docs = {c["source"] for c in chunks}
    print(f"Loaded {len(docs)} documents -> {len(chunks)} chunks")
    for c in chunks[:2]:
        print(f"\n[{c['id']}]\n{c['text'][:200]}...")
