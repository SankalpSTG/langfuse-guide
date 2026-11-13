"""Feature 5: prompt management.

Instead of hard-coding prompts, store them in Langfuse:
    - every save creates a new VERSION (1, 2, 3, ...)
    - a LABEL ("production", "staging", ...) points at one version
    - the app asks for a label, so moving the label changes the prompt live,
      and moving it back is a rollback. No redeploy.
    - "latest" is a built-in label that always points at the newest version.

A prompt can also carry a `config` (here: temperature), so model settings are
versioned together with the text.

Linking: passing `langfuse_prompt=prompt` to the LLM call records which prompt
version produced each generation. The Prompts page then shows latency, cost and
scores per version.

Caching: get_prompt() keeps prompts in memory (default 60 s) and refreshes them
in the background, so this adds no latency to normal requests.
"""

from langfuse import get_client, observe

from lflab import llm

PROMPT_NAME = "concise-answer"


def push(system_text: str, temperature: float, labels: list[str]) -> None:
    prompt = get_client().create_prompt(
        name=PROMPT_NAME,
        type="chat",
        prompt=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": "{{question}}"},  # {{variables}} are filled by compile()
        ],
        config={"temperature": temperature},
        labels=labels,
        commit_message="pushed from lflab",
    )
    print(f"saved {PROMPT_NAME} version {prompt.version} with labels {labels}")


def set_labels(version: int, labels: list[str]) -> None:
    """Promote or roll back: point labels at a version. A label lives on one version
    at a time, so adding "production" here removes it from the old version."""
    get_client().update_prompt(name=PROMPT_NAME, version=version, new_labels=labels)
    print(f"{PROMPT_NAME} version {version} now has labels {labels}")


def show() -> None:
    langfuse = get_client()
    for label in ["production", "latest"]:
        prompt = langfuse.get_prompt(PROMPT_NAME, type="chat", label=label)
        print(f"[{label}] version {prompt.version}, config {prompt.config}")
        print(f"  system: {prompt.prompt[0]['content']}\n")


@observe(name="prompted-answer")
def answer_with_prompt(question: str, label: str) -> str:
    prompt = get_client().get_prompt(PROMPT_NAME, type="chat", label=label)
    messages = prompt.compile(question=question)
    return llm.chat(
        messages,
        name="answer",
        temperature=prompt.config["temperature"],
        langfuse_prompt=prompt,
    )


def run(question: str, label: str) -> None:
    langfuse = get_client()
    trace_id = langfuse.create_trace_id()
    print(answer_with_prompt(question, label, langfuse_trace_id=trace_id))
    print(f"\ntrace: {langfuse.get_trace_url(trace_id=trace_id)}")
