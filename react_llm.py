#!/usr/bin/env python3
"""
react_llm.py
A ReAct agent where a language model writes each Thought and Action.
The loop executes the chosen tool, feeds the Observation back, and the model
revises its plan when an Observation is an error (dynamic replanning).

Supported Backends:
- Anthropic Claude (if ANTHROPIC_API_KEY is set in environment)
- Ollama local model (default fallback: qwen2.5:3b if no API key is provided)

Environment variables:
- ANTHROPIC_API_KEY: your Anthropic API key
- MODEL: model name (e.g., 'claude-haiku-5-5', 'claude-3-5-haiku-20241022', or 'qwen2.5:3b')
- PROVIDER: 'anthropic' or 'ollama' (autodetected if omitted)
"""
import os
import re
import json

from react_replan import TOOLS, GOAL, ORIGIN, DEST, DATE, PAX

PROVIDER = os.environ.get("PROVIDER")
if not PROVIDER:
    PROVIDER = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "ollama"

if PROVIDER == "anthropic":
    MODEL = os.environ.get("MODEL", "claude-haiku-5-5")
else:
    MODEL = os.environ.get("MODEL", "qwen2.5:3b")

MAX_STEPS = 12

SYSTEM = f"""You are a ReAct travel-booking agent.
Goal: {GOAL}

Tools (call with one JSON object of arguments):
- search_direct {{"origin": str, "dest": str, "date": str}}
- search_connecting {{"origin": str, "dest": str, "date": str}}
- search_bus {{"origin": str, "dest": str, "date": str}}
- book {{"name": str, "pax": int}}

Booking details: origin "{ORIGIN}", destination "{DEST}", date "{DATE}", passengers {PAX}.
Search results show fares per person but not seat counts. Seats are only checked when you book.

Reply in exactly one of these two formats each turn, one action per turn:

Thought: <your reasoning, your current plan, and any assumptions you are making>
Action: <tool_name> <JSON arguments on one line>

Thought: <your reasoning>
Final: <the answer for the user, summarising what you booked and the options you considered>

Guidelines:
1. Always strive to secure the lowest cost option that actually has available seats.
2. If an Observation contains an "error" (such as a WAITLIST or 0 seats), explicitly identify which assumption was false in your Thought, revise your plan, explore alternative routes (connecting trains or buses), and book the cheapest available option.
3. Do not repeat a failed booking or action unchanged."""


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


def query_llm(messages):
    """Send conversation history to the configured LLM provider."""
    if PROVIDER == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=MODEL, max_tokens=800, system=SYSTEM, messages=messages
        )
        return resp.content[0].text
    elif PROVIDER == "ollama":
        import ollama
        ollama_messages = [{"role": "system", "content": SYSTEM}] + messages
        resp = ollama.chat(
            model=MODEL,
            messages=ollama_messages,
            options={"temperature": 0}
        )
        return resp["message"]["content"]
    else:
        raise ValueError(f"Unsupported provider: {PROVIDER}")


def run():
    print(f"--- ReAct Agent Starting (Provider: {PROVIDER}, Model: {MODEL}) ---")
    print(f"Goal: {GOAL}\n")

    messages = [
        {"role": "user", "content": "Begin. Assume the cheapest direct train is the best option, then plan and act."}
    ]
    replans = 0

    for step in range(1, MAX_STEPS + 1):
        text = query_llm(messages)
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
