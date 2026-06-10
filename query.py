

import os
import sys

from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

from index import EMBED_MODEL, get_collection

load_dotenv()

TOP_K = 4
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an unofficial fan guide to the Amazon series "The Boys".

You must answer ONLY using the numbered CONTEXT passages provided with each
question. Follow these rules strictly:

1. Ground every claim in the CONTEXT. Do not use outside knowledge, even if you
   think you know the answer.
2. If the CONTEXT does not contain enough information to answer, say exactly:
   "I don't have enough information in my sources to answer that." Do not guess.
3. After your answer, add a line beginning with "Sources:" listing the source
   file name(s) of the passages you actually used.
4. Keep answers concise and factual. Do not invent quotes, episode numbers, or
   character details that are not in the CONTEXT."""


def format_context(documents: list[str], sources: list[str]) -> str:
    blocks = []
    for i, (doc, src) in enumerate(zip(documents, sources), start=1):
        blocks.append(f"[{i}] (source: {src})\n{doc}")
    return "\n\n".join(blocks)


def retrieve(question: str, model, collection, k: int = TOP_K):
    q_embedding = model.encode([question]).tolist()
    results = collection.query(query_embeddings=q_embedding, n_results=k)
    documents = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]
    distances = results["distances"][0]
    return documents, sources, distances


def answer(question: str, model, collection, client) -> str:
    documents, sources, _ = retrieve(question, model, collection)
    context = format_context(documents, sources)
    user_message = f"CONTEXT:\n{context}\n\nQUESTION: {question}"

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content


def main():
    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit("GROQ_API_KEY not set. Copy .env.example to .env and add your key.")

    print("Loading embedding model + vector store ...")
    model = SentenceTransformer(EMBED_MODEL)
    collection = get_collection()
    if collection.count() == 0:
        raise SystemExit("Vector store is empty. Run `python index.py` first.")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # Single-shot mode: question passed as a command-line argument.
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(f"\nQ: {question}\n")
        print(answer(question, model, collection, client))
        return

    # Interactive chat loop.
    print("\nUnofficial Guide to The Boys — ask me anything (type 'quit' to exit).\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"quit", "exit", "q"}:
            break
        if not question:
            continue
        print("\nGuide:", answer(question, model, collection, client), "\n")


if __name__ == "__main__":
    main()
