"""Feature 8: LLM-as-a-judge on production traces (online evaluation).

Experiments score a fixed dataset. This scores REAL traffic after the fact:
fetch recent `ask` traces, have an LLM grade each answer, write the grade back
as a score on the trace. Same idea as Langfuse's managed evaluators in the UI,
but done from code with `run_batched_evaluation`.

The pieces:
    filter      which observations to evaluate (JSON, same format as the API)
    mapper      turns one observation into {input, output, ...} for evaluators
    evaluators  same Evaluation functions an experiment uses
"""

import json

from langfuse import Evaluation, EvaluatorInputs, get_client, observe

from lflab import llm


def mapper(*, item, **kwargs) -> EvaluatorInputs:
    return EvaluatorInputs(input=item.input, output=item.output, expected_output=None, metadata=None)


# The judge's own LLM call is traced too, typed "evaluator" so it is easy to
# tell apart from real user traffic.
@observe(name="helpfulness-judge", as_type="evaluator")
def helpfulness(*, input, output, **kwargs) -> Evaluation:
    verdict = llm.chat(
        [
            {
                "role": "user",
                "content": (
                    "Rate how helpful this answer is, from 0 (useless) to 1 (excellent).\n"
                    f"Question: {input}\nAnswer: {output}\n"
                    'Reply with JSON only: {"score": <number>, "reason": "<one sentence>"}'
                ),
            }
        ],
        name="judge-call",
        response_format={"type": "json_object"},
    )
    parsed = json.loads(verdict)
    return Evaluation(name="helpfulness", value=float(parsed["score"]), comment=parsed["reason"])


def run(trace_name: str, limit: int) -> None:
    only_roots_named = json.dumps(
        [
            {"type": "string", "column": "name", "operator": "=", "value": trace_name},
            {"type": "boolean", "column": "isRootObservation", "operator": "=", "value": True},
        ]
    )
    result = get_client().run_batched_evaluation(
        filter=only_roots_named,
        mapper=mapper,
        evaluators=[helpfulness],
        max_items=limit,
        max_concurrency=2,
    )
    print(f"evaluated {result.total_items_processed} '{trace_name}' traces, "
          f"created {result.total_scores_created} scores")
