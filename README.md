# The Unofficial Guide — Project 1

> A retrieval-augmented (RAG) fan guide to the Amazon Prime series **_The Boys_**.
> Ask it questions in natural language; it answers using only a corpus of fan-guide
> documents and cites its sources.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # then put your real GROQ_API_KEY in .env
python index.py               # build the vector store (one time)
python query.py               # interactive chat — type 'quit' to exit
python query.py "your question here"   # single-shot mode
```

Pipeline: `documents/*.txt` → **ingest.py** (chunk) → **index.py** (embed + ChromaDB) →
**query.py** (retrieve top-k + Groq grounded generation).

---

## Domain

This system is an **unofficial fan guide to _The Boys_** — its characters (Homelander, Butcher,
Starlight, Hughie, Soldier Boy, Stormfront), its core lore (Compound V, Vought International, the
Seven), its themes and satire, and its most-discussed plot moments.

The knowledge is valuable because the show's actual meaning lives in fan interpretation, not official
marketing. The premise of the series is that the "heroes" are villains, so official synopses and
in-universe promotional framing are deliberately misleading — the official channel is the satirical
target. The genuinely useful information (who is secretly evil, what Compound V really is, why a scene
matters thematically) lives in fan wikis, subreddit threads, and video-essay analysis, making it hard
to find through official channels by design.

---

## Document Sources

| #  | Source | Type | URL or file path |
|----|--------|------|-----------------|
| 1  | r/TheBoys character breakdown — "Homelander, explained" | Fan character analysis | `documents/01_homelander_character.txt` |
| 2  | Fan wiki profile — Billy Butcher | Character analysis | `documents/02_butcher_character.txt` |
| 3  | Forum explainer — "What is Compound V?" | Lore explainer | `documents/03_compound_v.txt` |
| 4  | Wiki overview — Vought International | Worldbuilding / satire | `documents/04_vought_corporation.txt` |
| 5  | Fan roster guide — "The Seven, member by member" | Reference / roster | `documents/05_the_seven_roster.txt` |
| 6  | Character arc essay — Starlight | Character analysis | `documents/06_starlight_arc.txt` |
| 7  | Character arc discussion — Hughie Campbell | Character analysis | `documents/07_hughie_arc.txt` |
| 8  | Fan analysis — Soldier Boy & Stormfront | Character / theme analysis | `documents/08_soldier_boy_stormfront.txt` |
| 9  | Video-essay summary — "What The Boys is really about" | Thematic analysis | `documents/09_themes_satire.txt` |
| 10 | Episode megathread digest — "Most talked-about moments" | Episode / plot reference | `documents/10_episodes_moments.txt` |

The sources are intentionally varied — character profiles, lore explainers, corporate/worldbuilding
overview, thematic essay, and an episode digest — so the corpus covers distinct subtopics rather than
repeating one perspective.

---

## Chunking Strategy

**Chunk size:** 600 characters

**Overlap:** 100 characters

**Why these choices fit your documents:** Each document is a short, single-topic fan-guide entry
(~1–2k characters) built from a few tight paragraphs. A 600-character window holds roughly one
paragraph — a coherent unit of meaning such as one character trait or one lore fact — without bundling
unrelated ideas that would dilute the embedding. The 100-character overlap (about one sentence) keeps a
fact that straddles a boundary from being orphaned: a sentence that ends one chunk but completes a
thought beginning the next is preserved in both. I used character-based splitting (rather than
token-based) because the documents are plain prose with no structure to exploit, and at this scale
characters are a good enough proxy for tokens. Preprocessing: `.strip()` on each chunk to drop edge
whitespace; the human-readable `SOURCE:`/`TYPE:` provenance header stays in the text so it can surface
in retrieved context.

**Final chunk count:** 34 chunks across 10 documents.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dimensional, runs locally, no API
cost). Retrieval uses cosine similarity in a persistent ChromaDB collection, with **top-k = 4**.

**Production tradeoff reflection:** MiniLM is small, fast, and free — ideal for a local project — but it
caps input around 256 word-pieces and is English-only with general-domain training. Deploying for real
users with no cost constraint, I'd weigh: (1) a stronger model (`all-mpnet-base-v2`, or an API model
like OpenAI `text-embedding-3-large` / Voyage) for better accuracy on fan jargon — "Temp V,"
"Herogasm," character nicknames — that MiniLM may under-weight; (2) **context length**, since a
longer-context model would let me embed larger chunks without truncation; (3) **multilingual** support
if the fanbase posts in other languages; (4) **latency vs. accuracy**, since API models add network
round-trips, so for an interactive chat I'd cache embeddings and possibly keep a local model if p95
latency mattered. The honest tradeoff is domain-jargon accuracy and context length (favoring a bigger
model) against latency, privacy, and operational simplicity (favoring local MiniLM).

---

## Grounded Generation

**System prompt grounding instruction:** The model is told it is an unofficial fan guide that must
answer **only** from the numbered CONTEXT passages, with these explicit rules (verbatim from
`query.py`):

> 1. Ground every claim in the CONTEXT. Do not use outside knowledge, even if you think you know the answer.
> 2. If the CONTEXT does not contain enough information to answer, say exactly: "I don't have enough information in my sources to answer that." Do not guess.
> 3. After your answer, add a line beginning with "Sources:" listing the source file name(s) of the passages you actually used.
> 4. Keep answers concise and factual. Do not invent quotes, episode numbers, or character details that are not in the CONTEXT.

Structural choices reinforce this: each retrieved chunk is injected as a numbered block labeled with
its source file (`[1] (source: 03_compound_v.txt)\n...`), the question is appended after the context in
the user message, and generation runs at **temperature 0.2** to suppress creative drift. This was
verified to work — an out-of-scope question ("What is the name of A-Train's brother?") triggered the
exact refusal string instead of a hallucination (see Failure Case Analysis).

**How source attribution is surfaced in the response:** Every answer ends with a `Sources:` line naming
the document file(s) the model used, so the user can trace any claim back to a specific document.

---

## Evaluation Report

Run on the live pipeline (`all-MiniLM-L6-v2` + ChromaDB top-k=4 + Groq `llama-3.3-70b-versatile`).

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What is Compound V and where did it come from? | Vought chemical, roots in Nazi scientist Frederick Vought (WWII), injected into infants to create supes. | "Compound V is a fictional chemical that creates supes. Developed by Vought International, roots tracing back to Nazi scientist Frederick Vought during WWII." | Relevant | Accurate |
| 2 | Who killed Hughie's girlfriend and how did it happen? | A-Train ran through Robin at super speed in the pilot. | "A-Train killed Hughie's girlfriend, Robin, by running through her at super speed, vaporizing her instantly." Sources: 07_hughie_arc.txt | Relevant | Accurate |
| 3 | What are Homelander's powers and his core psychological flaw? | Flight, heat/laser vision, super strength, super hearing, near-invulnerable; approval-addicted, raised loveless in a Vought lab. | "Laser/heat vision, flight, enhanced hearing. Core flaw: obsessed with adoration/ratings; conditioned to crave approval, raised in a lab without love." Sources: 01_homelander_character.txt | Relevant | Accurate (partial power list) |
| 4 | Why do fans consider Vought the real villain rather than any single supe? | Vought created and hid Compound V and built an economy on lies — systemic corporate evil over any individual. | "Because the company created Compound V, hid it, and built an entire economy on lies." Sources: 04_vought_corporation.txt | Relevant | Accurate |
| 5 | Who is Stormfront really, and what does she represent? | Klara Risinger, a literal Nazi and early Compound V subject; satire of internet-laundered white supremacy. | "Klara Risinger, a literal Nazi and one of the first Compound V test subjects under Frederick Vought in WWII Germany. Represents satire of white-supremacist ideology laundering itself through internet culture." Sources: 08_soldier_boy_stormfront.txt | Relevant | Accurate |

**Retrieval quality:** Relevant (5/5) — every question retrieved chunks from the correct source document.
**Response accuracy:** Accurate (5/5). Q3 is accurate but slightly abbreviated — the model omitted
super strength / near-invulnerability, which were present in the source document (see below).

---

## Failure Case Analysis

**Question that failed:** *"What are Homelander's powers and what is his core psychological flaw?"* (Q3)
— a partial-recall failure — plus a deliberate out-of-scope probe, *"What is the name of A-Train's
brother and what are his powers?"*

**What the system returned:** For Q3, the model listed laser/heat vision, flight, and enhanced hearing
but **omitted super strength and near-invulnerability**, even though the source document
(`01_homelander_character.txt`) explicitly states them. For the out-of-scope probe, the system
correctly returned the exact refusal: *"I don't have enough information in my sources to answer that."*

**Root cause (tied to a specific pipeline stage):** This is a **chunking + retrieval** interaction. The
super-strength/invulnerability sentence and the laser-vision sentence sit in different parts of the
Homelander document and landed in **different chunks**. With top-k=4, retrieval surfaced the chunk
containing the laser-vision and psychology material (the strongest match for "powers" + "flaw") but did
not rank the chunk holding "super strength / bulletproof" highly enough to include it. The model
answered faithfully from the context it received — so the gap is in retrieval coverage, not generation.
The out-of-scope probe "failed" by design and is actually a success: A-Train has no brother in the
corpus, the grounding prompt suppressed a guess, and the refusal fired correctly.

**What you would change to fix it:** (1) Increase top-k from 4 to ~6 so more chunks of the same
document are pulled in for broad "list all the powers" questions; (2) reduce chunk size or increase
overlap so a single character's complete power set stays within one retrievable unit; or (3) add a
light re-ranking / source-grouping step that, when multiple chunks share a source, merges them before
generation so the model sees the full profile rather than one fragment.

---

## Spec Reflection

**One way the spec helped you during implementation:** Writing the Chunking Strategy and Retrieval
Approach in `planning.md` first meant the implementation was just translation, not invention. Because I
had already committed to 600/100 character chunks and `all-MiniLM-L6-v2` with top-k=4 and justified
*why*, I could hand those exact numbers to the AI tool and the generated `ingest.py`/`index.py` matched
my intent on the first pass. The Evaluation Plan was especially valuable: having 5 concrete questions
with expected answers written in advance turned testing into a checklist instead of an open-ended "does
this seem okay" guess, and it surfaced the Q3 partial-recall issue immediately.

**One way your implementation diverged from the spec, and why:** The spec's grounding plan expected the
`Sources:` line to name files cleanly, but in testing the LLM sometimes echoes the numbered context
label (e.g. "01_compound_v.txt", "02_compound_v.txt") rather than the true filename, because three
chunks from the same document were retrieved and the model paraphrased the bracket indices. I left the
behavior as-is for this submission since attribution still points the user to the right document, but
the spec-accurate fix would be to format each context block with the filename only once per source, or
to post-process the model's Sources line against the actual retrieved metadata. This is a small
generation-formatting divergence, not a grounding failure — the underlying retrieved sources were
always correct.

---

## AI Usage

**Instance 1 — Implementing the chunking + ingestion stage**

- *What I gave the AI:* The Domain, Documents, and Chunking Strategy sections of my `planning.md`,
  including the decision to use 600-character chunks with 100-character overlap and the reasoning that
  my documents are short single-topic entries.
- *What it produced:* `ingest.py` with `load_documents()` and a `chunk_text()` function implementing a
  sliding character window with overlap, plus a `build_chunks()` helper that tags each chunk with a
  stable `source::chunkN` id.
- *What I changed or overrode:* I kept the `SOURCE:`/`TYPE:` provenance headers inside the chunk text
  (rather than stripping them) so source context could ride along into retrieval, and I added a `.pdf`
  branch guarded behind a lazy `pdfplumber` import so the script doesn't require pdfplumber unless a PDF
  is actually present.

**Instance 2 — Designing the grounded-generation system prompt**

- *What I gave the AI:* The Grounded Generation requirement and a request for a system prompt that
  forbids out-of-context answers, forces a fixed refusal string, and requires source citation.
- *What it produced:* A four-rule system prompt plus a numbered-context formatting scheme and a
  temperature setting.
- *What I changed or overrode:* I lowered the temperature to 0.2 (from a more creative default) to
  reduce drift, pinned the exact refusal wording so I could test for it programmatically, and verified
  the refusal actually fires by running an out-of-scope question ("A-Train's brother") — which is now
  documented as the failure case. I also confirmed the abstention behavior rather than trusting that the
  instruction alone would work.

---

## Files

```
documents/                10 fan-guide .txt sources
ingest.py                 Stage 1+2: ingestion + chunking
index.py                  Stage 3: embedding + ChromaDB vector store
query.py                  Stage 4+5: retrieval + grounded generation (CLI)
planning.md               Pre-build spec
README.md                 This report
requirements.txt          Dependencies
```
