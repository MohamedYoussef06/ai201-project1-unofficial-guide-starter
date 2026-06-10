# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

This system is an **unofficial fan guide to the Amazon Prime series _The Boys_** — covering its
characters (Homelander, Butcher, Starlight, Hughie, Soldier Boy, Stormfront), its central lore
(Compound V, Vought International, the Seven), its themes/satire, and its most-discussed plot moments.

This knowledge is valuable because the show's meaning lives in fan interpretation, not in official
marketing. Amazon's and Vought's (in-universe) promotional materials deliberately present the supes as
heroes — the whole point of the show is that they aren't. The genuinely useful knowledge (who is
secretly a villain, what Compound V really is, why a scene matters thematically) comes from fan wikis,
subreddit discussions, and video-essay analysis, not from official episode synopses. It is "hard to
find through official channels" by design: the official channel is the satirical target.

---

## Documents

10 source documents, each a short self-contained fan-guide entry, stored as `.txt` files in
`documents/`. Together they span characters, lore, the corporation, themes, and episodes so the corpus
covers different subtopics rather than repeating one perspective.

| #  | Source | Description | URL or location |
|----|--------|-------------|-----------------|
| 1  | r/TheBoys character breakdown | Homelander — powers, psychology, key scenes | `documents/01_homelander_character.txt` |
| 2  | Fan wiki profile | Billy Butcher — motivation, Temp V, Hughie dynamic | `documents/02_butcher_character.txt` |
| 3  | Forum lore explainer | Compound V — origin, Temp V, public reveal | `documents/03_compound_v.txt` |
| 4  | Wiki overview | Vought International — corporate satire, Stan Edgar | `documents/04_vought_corporation.txt` |
| 5  | Fan roster guide | The Seven — member-by-member breakdown | `documents/05_the_seven_roster.txt` |
| 6  | Character arc essay | Starlight — believer-to-rebel arc, powers | `documents/06_starlight_arc.txt` |
| 7  | Character arc discussion | Hughie — Robin's death, Temp V, role | `documents/07_hughie_arc.txt` |
| 8  | Fan analysis | Soldier Boy & Stormfront — political villains | `documents/08_soldier_boy_stormfront.txt` |
| 9  | Video-essay summary | Themes & satire of the series | `documents/09_themes_satire.txt` |
| 10 | Episode megathread digest | Most talked-about plot moments | `documents/10_episodes_moments.txt` |

---

## Chunking Strategy

**Chunk size:** 600 characters

**Overlap:** 100 characters

**Reasoning:** Each document is a short, single-topic fan-guide entry (~1–2k characters) made of a few
tight paragraphs. A 600-character window holds roughly one paragraph — a coherent unit of meaning (one
character trait, one lore fact) — without bundling unrelated ideas that would dilute the embedding. The
100-character overlap (~one sentence) keeps facts that straddle a boundary from being orphaned, e.g. a
sentence ending one chunk that completes a thought beginning in the next. Character-based splitting is
used rather than token-based because the documents are plain prose with no special structure to exploit,
and characters are a good enough proxy at this scale. Final corpus: **34 chunks across 10 documents.**

---

## Retrieval Approach

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim, runs locally, no API cost).

**Top-k:** 4 chunks retrieved per query.

**Production tradeoff reflection:** MiniLM is small, fast, and free, which is ideal for a local class
project, but it caps input at 256 word-pieces and is English-only with general-domain training. If I
deployed this for real users and cost weren't a concern, I'd weigh: (1) a larger model like
`all-mpnet-base-v2` or an API model (OpenAI `text-embedding-3-large`, Voyage) for higher accuracy on
nuanced fan-jargon ("Temp V," "Herogasm," character nicknames) that MiniLM may treat as low-signal;
(2) **context length** — a longer-context model would let me embed bigger chunks without truncation;
(3) **multilingual** support if the fanbase posts in other languages; (4) **latency vs. accuracy** —
API models add network round-trips, so for an interactive chat I'd cache embeddings and accept slightly
lower accuracy locally if p95 latency mattered. The honest tradeoff is accuracy-on-domain-jargon and
context length (favoring a bigger model) against latency, privacy, and operational simplicity (favoring
local MiniLM).

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What is Compound V and where did it come from? | A Vought chemical (roots in Nazi scientist Frederick Vought) injected into infants to create supes; no supe is naturally born. |
| 2 | Who killed Hughie's girlfriend and how? | A-Train, by running through Robin at super speed in the pilot. |
| 3 | What are Homelander's powers and what is his core psychological flaw? | Flight, heat/laser vision, super strength, near-invulnerability, super hearing; deeply insecure, approval-addicted, raised loveless in a lab. |
| 4 | Why do fans consider Vought the real villain rather than any single supe? | Vought manufactures and hides Compound V, manages supes as brand assets, and covers up harm — the corporation, not any individual, is the systemic evil. |
| 5 | Who is Stormfront really, and what does she represent? | A literal Nazi (originally Klara Risinger), one of the first Compound V subjects; satire of internet-laundered white supremacy. |

---

## Anticipated Challenges

1. **Chunk-boundary splitting of key facts.** Some facts (e.g. Soldier Boy being Homelander's father, or
   the full Compound V origin) are stated in one sentence that could land near a chunk edge. If retrieval
   returns the chunk that holds only half the fact, the model gets incomplete context. Mitigation: 100-char
   overlap and retrieving top-k=4 so adjacent chunks are likely both returned.

2. **Off-topic / cross-character retrieval.** Many documents mention overlapping entities (Homelander
   appears in the Seven, Stormfront, Soldier Boy, and themes docs). A query about one character may pull
   chunks that mention them only in passing while discussing someone else, lowering precision. Mitigation:
   cosine similarity + a focused, single-topic-per-document corpus to keep the strongest match on-topic.

---

## Architecture

```
                THE BOYS — UNOFFICIAL GUIDE (RAG PIPELINE)

  [1] DOCUMENT INGESTION        documents/*.txt
        |                       ingest.py  (Python stdlib, pdfplumber optional)
        v
  [2] CHUNKING                  600-char windows, 100-char overlap
        |                       ingest.py :: chunk_text()
        v
  [3] EMBEDDING + VECTOR STORE  all-MiniLM-L6-v2  ->  ChromaDB (cosine, persistent)
        |                       index.py  (sentence-transformers + chromadb)
        v
  [4] RETRIEVAL                 embed query -> top-k=4 nearest chunks
        |                       query.py :: retrieve()
        v
  [5] GENERATION (CLI)          Groq llama-3.3-70b-versatile, grounded system prompt
                                query.py :: answer()  ->  answer + Sources line
```

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:**
Use **Claude (Claude Code)**. Input: the Domain, Documents, and Chunking Strategy sections of this
planning.md plus the chosen 600/100 chunk parameters. Expected output: `ingest.py` with `load_documents()`
and `chunk_text()` implementing character-window chunking with overlap. Verify by running `python ingest.py`
and checking the document and chunk counts and a sample chunk are sensible (got 10 docs → 34 chunks).

**Milestone 4 — Embedding and retrieval:**
Use **Claude**. Input: the Retrieval Approach section (model `all-MiniLM-L6-v2`, top-k=4, ChromaDB).
Expected output: `index.py` that embeds chunks and persists them to ChromaDB, and a `retrieve()` function
in `query.py`. Verify by running `python index.py` (confirm 34 chunks indexed) and inspecting that
retrieved chunks for a known question are topically correct.

**Milestone 5 — Generation and interface:**
Use **Claude**. Input: the Grounded Generation requirement + the system-prompt grounding rules.
Expected output: a CLI loop in `query.py` that calls the Groq LLM with retrieved context and a grounding
system prompt that forbids out-of-context answers and requires a Sources line. Verify by running the 5
evaluation questions and confirming answers are grounded, cite sources, and that an out-of-scope question
triggers the "not enough information" refusal.
