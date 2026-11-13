"""lflab: one command per Langfuse feature. Run `lflab --help`.

Each command is a thin wrapper. The real code, with explanations, lives in
src/lflab/features/<feature>.py.
"""

from pathlib import Path

import typer
from langfuse import get_client

from lflab.config import check_langfuse_settings
from lflab.features import agent, ask, chat, costs, datasets, experiments, judge, masking, prompts, rag, stats

app = typer.Typer(help="Learn Langfuse by running it.", no_args_is_help=True)
prompt_app = typer.Typer(help="Prompt management: versions, labels, linking.", no_args_is_help=True)
dataset_app = typer.Typer(help="Datasets: test sets for experiments.", no_args_is_help=True)
app.add_typer(prompt_app, name="prompt")
app.add_typer(dataset_app, name="dataset")


@app.callback()
def setup(ctx: typer.Context) -> None:
    check_langfuse_settings()
    # The SDK sends data in the background, in batches. A CLI exits quickly,
    # so we flush once at the end or the last spans would be lost.
    ctx.call_on_close(lambda: get_client().flush())


@app.command()
def doctor() -> None:
    """Check that the Langfuse keys and URL work."""
    ok = get_client().auth_check()
    print("Langfuse connection OK" if ok else "Langfuse rejected the keys")


@app.command("ask")
def ask_cmd(
    question: str,
    user: str = typer.Option("demo-user", help="Stored as the trace's user_id."),
    tag: list[str] = typer.Option(["cli"], help="Trace tags. Repeat for several."),
) -> None:
    """1. Tracing basics: @observe, generations, user_id, tags."""
    ask.run(question, user, tag)


@app.command("chat")
def chat_cmd(user: str = typer.Option("demo-user")) -> None:
    """2. Sessions + user feedback scores (multi-turn chat)."""
    chat.run(user)


@app.command("rag")
def rag_cmd(question: str, top_k: int = typer.Option(3)) -> None:
    """3. Nested spans: guardrail, retriever, generation."""
    rag.run(question, top_k)


@app.command("agent")
def agent_cmd(task: str, max_steps: int = typer.Option(5)) -> None:
    """4. Agent + tool observations."""
    agent.run(task, max_steps)


@prompt_app.command("push")
def prompt_push(
    system: str = typer.Option(..., help="The system prompt text."),
    temperature: float = typer.Option(..., help="Stored in the prompt's config."),
    label: list[str] = typer.Option([], help="Labels for this version, e.g. production."),
) -> None:
    """5a. Save a new prompt version."""
    prompts.push(system, temperature, label)


@prompt_app.command("label")
def prompt_label(
    version: int = typer.Option(...), label: list[str] = typer.Option(..., help="e.g. production")
) -> None:
    """5b. Promote or roll back by moving a label to a version."""
    prompts.set_labels(version, label)


@prompt_app.command("show")
def prompt_show() -> None:
    """5c. Show what 'production' and 'latest' point at."""
    prompts.show()


@prompt_app.command("run")
def prompt_run(question: str, label: str = typer.Option("production")) -> None:
    """5d. Answer using the prompt version behind a label."""
    prompts.run(question, label)


@dataset_app.command("upload")
def dataset_upload(
    name: str = typer.Option("qa-basics"),
    file: Path = typer.Option(Path("data/qa.json"), exists=True),
) -> None:
    """6a. Create a dataset from a JSON file."""
    datasets.upload(name, file)


@dataset_app.command("add-trace")
def dataset_add_trace(
    trace_id: str, expected: str = typer.Option(...), name: str = typer.Option("qa-basics")
) -> None:
    """6b. Turn a real trace into a dataset item."""
    datasets.add_trace(name, trace_id, expected)


@app.command("experiment")
def experiment_cmd(
    dataset: str = typer.Option("qa-basics"),
    label: str = typer.Option("production", help="Prompt label to test."),
    run_name: str = typer.Option(..., help="Unique name for this run, e.g. prod-v1."),
) -> None:
    """7. Run the prompt over a dataset and score every answer."""
    experiments.run(dataset, label, run_name)


@app.command("judge")
def judge_cmd(trace_name: str = typer.Option("ask"), limit: int = typer.Option(10)) -> None:
    """8. LLM-as-a-judge: score existing traces."""
    judge.run(trace_name, limit)


@app.command("mask")
def mask_cmd(question: str, sample_rate: float = typer.Option(1.0)) -> None:
    """9. Redact PII before it reaches Langfuse; sampling."""
    masking.run(question, sample_rate)


@app.command("price")
def price_cmd(
    input_per_million: float = typer.Option(...), output_per_million: float = typer.Option(...)
) -> None:
    """10. Register a price for LLM_MODEL so Langfuse shows cost."""
    costs.set_price(input_per_million, output_per_million)


@app.command("stats")
def stats_cmd(days: int = typer.Option(1)) -> None:
    """11. Cost, latency, tokens and scores via the Metrics API."""
    stats.run(days)
