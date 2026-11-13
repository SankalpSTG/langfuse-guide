"""Feature 9: masking PII and sampling.

mask:
    A function the SDK runs on every input, output and metadata value BEFORE it
    leaves your machine. Use it to keep emails, phone numbers, card numbers and
    secrets out of your observability data.

sample_rate:
    0.0 to 1.0. The share of traces that get sent. At high traffic, 0.1 keeps
    10% of traces, which keeps the bill and the noise down. The decision is made
    per trace, so a kept trace is always complete.

Both are client settings, so this command builds its own Langfuse client
before anything else runs. (The other commands use get_client(), which builds
a default client from the LANGFUSE_* environment variables.)
"""

import re

from langfuse import Langfuse

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d -]{8,}\d")


def redact(data, **kwargs):
    if isinstance(data, str):
        return PHONE.sub("[PHONE]", EMAIL.sub("[EMAIL]", data))
    if isinstance(data, dict):
        return {key: redact(value) for key, value in data.items()}
    # tuple matters: @observe records a function's positional arguments as a tuple.
    if isinstance(data, (list, tuple)):
        return [redact(value) for value in data]
    return data


def run(question: str, sample_rate: float) -> None:
    Langfuse(mask=redact, sample_rate=sample_rate)  # becomes the client get_client() returns

    from lflab.features.ask import run as ask_run  # imported after the client exists

    ask_run(question, user_id="masking-demo", tags=["masking"])
    print("The LLM saw the real text. Langfuse only got the redacted version: open the trace.")
