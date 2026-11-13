"""Feature 7: experiments (offline evaluation).

An experiment = run your app over every dataset item, then score each output.
Langfuse stores each run, so you can compare runs side by side in the UI
(Datasets -> your dataset -> Runs). Typical question it answers:
"is prompt version 3 better than version 2?"

The three pieces:
    task             what your app does with one item (returns the output)
    evaluators       score ONE item  (here: exact match + LLM judge)
    run_evaluators   score the WHOLE run (here: average accuracy)
"""

import json

from langfuse import Evaluation, get_client

from lflab import llm
from lflab.features.prompts import answer_with_prompt


def make_task(label: str):
    def task(*, item, **kwargs) -> str:
        return answer_with_prompt(item.input, label)

    return task


def contains_expected(*, output, expected_output, **kwargs) -> Evaluation:
    # str(): Langfuse stores items as JSON, so an expected "6" comes back as the number 6.
    hit = str(expected_output).lower() in output.lower()
    return Evaluation(name="contains-expected", value=1 if hit else 0, data_type="BOOLEAN")


def llm_judge(*, input, output, expected_output, **kwargs) -> Evaluation:
    verdict = llm.chat(
        [
            {
                "role": "user",
                "content": (
                    "Grade the answer from 0 to 1 for correctness and brevity.\n"
                    f"Question: {input}\nReference: {expected_output}\nAnswer: {output}\n"
                    'Reply with JSON only: {"score": <number>, "reason": "<one sentence>"}'
                ),
            }
        ],
        name="judge",
        response_format={"type": "json_object"},
    )
    parsed = json.loads(verdict)
    return Evaluation(name="judge-score", value=float(parsed["score"]), comment=parsed["reason"])


def accuracy(*, item_results, **kwargs) -> Evaluation:
    values = [e.value for r in item_results for e in r.evaluations if e.name == "contains-expected"]
    return Evaluation(name="accuracy", value=sum(values) / len(values))


def run(dataset_name: str, label: str, run_name: str) -> None:
    dataset = get_client().get_dataset(dataset_name)
    result = dataset.run_experiment(
        name=f"prompt-{label}",
        run_name=run_name,
        description=f"concise-answer prompt, label {label}",
        task=make_task(label),
        evaluators=[contains_expected, llm_judge],
        run_evaluators=[accuracy],
        max_concurrency=2,  # stay inside free-tier rate limits
    )
    print(result.format())
