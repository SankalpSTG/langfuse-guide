"""Feature 10: cost tracking with a custom model price.

Langfuse computes cost = tokens x price. It ships prices for well-known models,
but a model like qwen on Groq is unknown, so its generations show tokens but
$0 cost. Fix: register a model definition.

    match_pattern  regex matched against the generation's model name
    input_price    USD per input token
    output_price   USD per output token

Only generations ingested AFTER this are priced. You can also send exact costs
yourself per call with `cost_details={...}` on a generation.
"""

import re

from langfuse import get_client

from lflab import llm


def set_price(input_per_million: float, output_per_million: float) -> None:
    model_name = llm.model()
    get_client().api.models.create(
        model_name=model_name,
        match_pattern=f"(?i)^{re.escape(model_name)}$",
        unit="TOKENS",
        input_price=input_per_million / 1_000_000,
        output_price=output_per_million / 1_000_000,
    )
    print(f"{model_name}: ${input_per_million}/M input tokens, ${output_per_million}/M output tokens")
