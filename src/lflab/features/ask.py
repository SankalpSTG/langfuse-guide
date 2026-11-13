"""Feature 1: tracing basics with the @observe decorator.

Vocabulary:
    trace        = one request end to end (here: one question -> one answer)
    observation  = one step inside a trace. Types: span (generic step),
                   generation (an LLM call), tool, retriever, agent, guardrail, ...

What happens when you run `lflab ask "..."`:
    1. @observe turns `ask()` into the root observation of a new trace.
       Its arguments become the input, its return value becomes the output.
    2. The LLM call inside it (via langfuse.openai) becomes a child "generation".
    3. propagate_attributes() stamps user_id, tags and metadata on the trace and
       on every observation created inside the `with` block.

Trace tree in the UI:
    ask (span)
    └── answer (generation)  model, tokens, latency, cost
"""

from langfuse import get_client, observe, propagate_attributes

from lflab import llm


@observe(name="ask")
def ask(question: str, user_id: str, tags: list[str]) -> str:
    with propagate_attributes(user_id=user_id, tags=tags, metadata={"source": "cli"}):
        return llm.chat(
            [
                {"role": "system", "content": "Answer in at most three sentences."},
                {"role": "user", "content": question},
            ],
            name="answer",
        )


def run(question: str, user_id: str, tags: list[str]) -> None:
    langfuse = get_client()
    trace_id = langfuse.create_trace_id()  # we pick the id so we can print a link

    # langfuse_trace_id is a special keyword @observe understands.
    reply = ask(question, user_id, tags, langfuse_trace_id=trace_id)

    print(reply)
    print(f"\ntrace: {langfuse.get_trace_url(trace_id=trace_id)}")
