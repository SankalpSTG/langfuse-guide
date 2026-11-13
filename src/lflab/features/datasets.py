"""Feature 6: datasets.

A dataset is a list of items: an `input` and (optionally) an `expected_output`.
It is your test set. Two common ways to fill it:
    1. upload a file of known questions and answers   -> `lflab dataset upload`
    2. save interesting production traces into it      -> `lflab dataset add-trace`
       (source_trace_id keeps the link back to the original trace)
"""

import json
from pathlib import Path

from langfuse import get_client


def upload(name: str, file: Path) -> None:
    langfuse = get_client()
    langfuse.create_dataset(name=name, description=f"uploaded from {file.name}")
    items = json.loads(file.read_text())
    for item in items:
        langfuse.create_dataset_item(
            dataset_name=name, input=item["input"], expected_output=item["expected_output"]
        )
    print(f"dataset {name}: added {len(items)} items")


def add_trace(name: str, trace_id: str, expected_output: str) -> None:
    langfuse = get_client()
    root = langfuse.api.observations.get_many(
        trace_id=trace_id, is_root_observation=True, fields="core,io", limit=1
    ).data[0]
    langfuse.create_dataset_item(
        dataset_name=name,
        input=root.input,
        expected_output=expected_output,
        source_trace_id=trace_id,
    )
    print(f"dataset {name}: added item from trace {trace_id}")
