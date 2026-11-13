"""The one place we talk to the LLM.

Langfuse ships a drop-in replacement for the OpenAI SDK:

    from openai import OpenAI            # before
    from langfuse.openai import OpenAI   # after

Nothing else changes. Every chat completion is now recorded in Langfuse as a
"generation" with the model name, input messages, output, token usage, latency
and (if Langfuse knows the model price) cost.

Groq and OpenRouter speak the same API as OpenAI, so we just point `base_url`
at them and use free open models.

The wrapper also accepts a few extra Langfuse-only keyword arguments:
    name=...             name of the generation in the UI
    langfuse_prompt=...  links the generation to a managed prompt version
    metadata=...         any extra key/values to store on the generation
"""

from langfuse.openai import OpenAI

from lflab.config import require


def client() -> OpenAI:
    return OpenAI(base_url=require("LLM_BASE_URL"), api_key=require("LLM_API_KEY"))


def model() -> str:
    return require("LLM_MODEL")


def chat(messages: list[dict], name: str, **extra) -> str:
    """Send messages, return the reply text. `extra` goes straight to the API call."""
    response = client().chat.completions.create(
        model=model(), messages=messages, name=name, **extra
    )
    return response.choices[0].message.content
