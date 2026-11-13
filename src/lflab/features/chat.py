"""Feature 2: sessions and user feedback scores.

Session:
    A chat has many turns. Each turn is its own trace, and all of them share one
    session_id. The Langfuse "Sessions" page then replays the whole conversation.

User feedback:
    After each answer you can type y or n. That becomes a BOOLEAN score attached
    to the turn's trace (name "user-feedback"). In a real app this is the
    thumbs up / thumbs down button. Scores are how you measure quality over time.
"""

import uuid

from langfuse import get_client, observe, propagate_attributes

from lflab import llm


@observe(name="chat-turn")
def turn(history: list[dict], session_id: str, user_id: str) -> tuple[str, str]:
    with propagate_attributes(session_id=session_id, user_id=user_id, tags=["chat"]):
        reply = llm.chat(history, name="chat-reply")
    trace_id = get_client().get_current_trace_id()
    return reply, trace_id


def run(user_id: str) -> None:
    langfuse = get_client()
    session_id = f"chat-{uuid.uuid4().hex[:8]}"
    history = [{"role": "system", "content": "You are a friendly, concise assistant."}]
    print(f"session {session_id}. Empty line to quit.\n")

    while True:
        question = input("you> ").strip()
        if not question:
            break

        history.append({"role": "user", "content": question})
        reply, trace_id = turn(history, session_id, user_id)
        history.append({"role": "assistant", "content": reply})
        print(f"bot> {reply}\n")

        feedback = input("helpful? [y/n, enter to skip]> ").strip().lower()
        if feedback in ("y", "n"):
            langfuse.create_score(
                trace_id=trace_id,
                name="user-feedback",
                value=1 if feedback == "y" else 0,
                data_type="BOOLEAN",
                comment="typed in the CLI",
            )

    print(f"Open Sessions in the Langfuse UI and pick {session_id} to replay this chat.")
