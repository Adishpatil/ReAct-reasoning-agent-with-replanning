#!/usr/bin/env python3
"""
react_llm.py
A ReAct agent where a language model writes each Thought and Action.
The loop executes the chosen tool, feeds the Observation back, and the model
revises its plan when an Observation is an error (dynamic replanning).

Requires: pip install anthropic   and   export ANTHROPIC_API_KEY=...
Optional: export MODEL=<model name>   (defaults to claude-haiku-5-5)
"""
import os
import re
import json

import anthropic
from react_replan import TOOLS, GOAL

MODEL = os.environ.get("MODEL", "claude-haiku-5-5")
MAX_STEPS = 12

SYSTEM = f"""You are a ReAct travel-booking agent.
Goal: {GOAL}

Tools (call with one JSON object of arguments):
- search_direct {{"origin": str, "dest": str, "date": str}}
- search_connecting {{"origin": str, "dest": str, "date": str}}
- search_bus {{"origin": str, "dest": str, "date": str}}
- book {{"name": str, "pax": int}}

Search results show fares but not seat counts. Seats are only checked when you book.

Reply in exactly one of these two formats each turn, one action per turn:

Thought: <your reasoning, your current plan, and any assumptions you are making>
Action: <tool_name> <JSON arguments on one line>

Thought: <your reasoning>
Final: <the answer for the user, summarising what you booked and the options you considered>

If an Observation contains an "error", state which assumption was wrong in your
Thought, revise your plan, and continue. Do not repeat a failed action unchanged."""


def parse(text):
    """Split a model reply into (thought, final_answer, (tool, args) or None)."""
    thought = re.search(r"Thought:\s*(.*?)(?=\n(?:Action|Final):|\Z)", text, re.S)
    final = re.search(r"Final:\s*(.*)", text, re.S)
    action = re.search(r"Action:\s*(\w+)\s*(\{[^}]*\})", text, re.S)
    parsed_action = (action.group(1), json.loads(action.group(2))) if action else None
    return (
        thought.group(1).strip() if thought else text.strip(),
        final.group(1).strip() if final else None,
        parsed_action,
    )


def run():
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": "Begin. Make your plan, then take the first action."}]
    replans = 0

    for step in range(1, MAX_STEPS + 1):
        resp = client.messages.create(
            model=MODEL, max_tokens=800, system=SYSTEM, messages=messages
        )
        text = resp.content[0].text
        print(f"\n[step {step}]\n{text}")
        messages.append({"role": "assistant", "content": text})

        _, final, action = parse(text)
        if final:
            print(f"\nFINAL ANSWER: {final}")
            print(f"Replans during run: {replans}")
            return

        if action is None:
            obs = {"error": "no valid Action or Final line; use the required format"}
        else:
            name, args = action
            if name not in TOOLS:
                obs = {"error": f"unknown tool '{name}'"}
            else:
                try:
                    obs = TOOLS[name](**args)
                except TypeError as e:
                    obs = {"error": f"bad arguments: {e}"}

        print(f"Observation: {obs}")
        if isinstance(obs, dict) and "error" in obs:
            replans += 1
            print("*** Error observation: the model must replan on the next turn")
        messages.append({"role": "user", "content": f"Observation: {obs}"})

    print("Stopped: step budget reached")


if __name__ == "__main__":
    run()
