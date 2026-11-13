"""Feature 4: tracing an agent that calls tools.

An agent is a loop: ask the LLM, run whatever tool it asks for, give it the
result, repeat until it answers. Langfuse has observation types for exactly this.

Trace tree in the UI (Langfuse also draws it as an agent graph):
    agent (agent)
    ├── think-1 (generation)   LLM decides to call a tool
    ├── calculator (tool)
    ├── think-2 (generation)   LLM decides it is done
    └── ...

@observe(as_type="tool") is all it takes to mark a function as a tool.
"""

import json
from datetime import datetime, timezone

from langfuse import get_client, observe

from lflab import llm


@observe(as_type="tool")
def calculator(expression: str) -> str:
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "error: only numbers and + - * / ( ) are allowed"
    return str(eval(expression))  # safe: only arithmetic characters reach here


@observe(as_type="tool")
def current_time() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


TOOLS = {"calculator": calculator, "current_time": current_time}

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate an arithmetic expression, e.g. (12 + 3) * 4",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "current_time",
            "description": "Current UTC date and time",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


@observe(name="agent", as_type="agent")
def agent(task: str, max_steps: int) -> str:
    messages = [
        {"role": "system", "content": "Use the tools for any arithmetic or time question. Be brief."},
        {"role": "user", "content": task},
    ]
    for step in range(1, max_steps + 1):
        response = llm.client().chat.completions.create(
            model=llm.model(), messages=messages, tools=TOOL_SPECS, name=f"think-{step}"
        )
        message = response.choices[0].message
        if not message.tool_calls:
            return message.content

        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            result = TOOLS[call.function.name](**arguments)
            print(f"  [tool] {call.function.name}({arguments}) -> {result}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    get_client().update_current_span(level="WARNING", status_message="hit max_steps")
    return "Stopped: too many steps."


def run(task: str, max_steps: int) -> None:
    langfuse = get_client()
    trace_id = langfuse.create_trace_id()
    print(agent(task, max_steps, langfuse_trace_id=trace_id))
    print(f"\ntrace: {langfuse.get_trace_url(trace_id=trace_id)}")
