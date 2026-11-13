"""Feature 3: a RAG pipeline traced with context managers and observation types.

@observe is handy for whole functions. When you want to trace a few lines, use
the context manager instead:

    with langfuse.start_as_current_observation(name="...", as_type="retriever") as obs:
        ...
        obs.update(output=...)

Anything started inside the `with` block becomes a child of `obs`.

Trace tree in the UI:
    rag (chain)
    ├── input-check (guardrail)   blocks prompt-injection style questions
    ├── search-knowledge (retriever)
    └── answer (generation)

The knowledge base is data/knowledge.json: facts about Langfuse itself, so the
demo doubles as study notes. Retrieval is plain word overlap to keep it simple.
"""

import json
from pathlib import Path

from langfuse import get_client

from lflab import llm

KNOWLEDGE = json.loads((Path(__file__).parents[3] / "data" / "knowledge.json").read_text())
BLOCKED_PHRASES = ["ignore previous instructions", "system prompt", "reveal your prompt"]


def words(text: str) -> set[str]:
    return {w.strip(".,?!()").lower() for w in text.split() if len(w) > 3}


def search(question: str, top_k: int) -> list[str]:
    ranked = sorted(KNOWLEDGE, key=lambda doc: len(words(doc) & words(question)), reverse=True)
    return [doc for doc in ranked[:top_k] if words(doc) & words(question)]


def run(question: str, top_k: int) -> None:
    langfuse = get_client()

    with langfuse.start_as_current_observation(name="rag", as_type="chain", input=question) as root:
        with langfuse.start_as_current_observation(name="input-check", as_type="guardrail", input=question) as guard:
            blocked = any(phrase in question.lower() for phrase in BLOCKED_PHRASES)
            guard.update(output={"blocked": blocked})
            if blocked:
                # level=WARNING makes this trace easy to filter in the UI.
                guard.update(level="WARNING", status_message="prompt injection attempt")
                root.update(output="Refused.", level="WARNING")
                print("Refused: that looks like a prompt injection attempt.")
                return

        with langfuse.start_as_current_observation(name="search-knowledge", as_type="retriever", input=question) as retriever:
            docs = search(question, top_k)
            retriever.update(output=docs, metadata={"top_k": top_k, "found": len(docs)})
            if not docs:
                retriever.update(level="WARNING", status_message="nothing retrieved")

        context = "\n".join(f"- {doc}" for doc in docs)
        answer = llm.chat(
            [
                {"role": "system", "content": "Answer only from the context. If it is not there, say you don't know.\n\nContext:\n" + context},
                {"role": "user", "content": question},
            ],
            name="answer",
        )
        root.update(output=answer)

        # Score the trace right away: did retrieval find anything?
        root.score_trace(name="retrieval-hit", value=1 if docs else 0, data_type="BOOLEAN")
        trace_id = root.trace_id

    print(answer)
    print(f"\ntrace: {langfuse.get_trace_url(trace_id=trace_id)}")
